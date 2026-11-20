"""Phase 9 第三片：AI-04 目標回報端點（todo 9.10；spec 5.13「目標回報」第 1～7 點、5.3a〈AI-04〉；FR-GOL-06、07、AC-50）。

Dev-A 依 DA-27 暫代撰寫；只經 HTTP、SQL 種子與 FakeAIClient 操作，不讀實作。
測試清單與兩輪子代理審查紀錄：.scratch/phase9/testlist-9.10-v3.md（E 系列、T 系列）。
「比照週報」而 spec 未逐字寫明的行為（不呼叫 AI 時存的 ai_status、無成功初稿再失敗、PUT 更新 updated_at）依週報現行實作，PR 註明。
#47 Q7（任務改私人後草稿標題外露）裁定前照現行 spec，不在本檔。
"""

import json

import pytest
from sqlalchemy.exc import IntegrityError

from app.ai.client import AIInvalidOutput, AITimeout, AIUnavailable
from tests.acceptance.helpers import API, count

NOW = "2026-11-11T10:00:00+08:00"   # FixedClock
TS = "'2026-11-01T09:00+08:00'"
MARK = "機密標記XYZ"                 # 不可外送、不可留存的內容
KEYS = {"id", "goal_id", "ai_status", "excluded_private", "draft", "validated", "manual_text", "updated_at"}

BASE = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
 (1, '會員系統', 'work', 'manager', {TS}, {TS}),
 (3, '空專案', 'work', 'manager', {TS}, {TS}),
 (4, '家裡裝修', 'private', 'none', {TS}, {TS});
INSERT INTO goals (id, type, title, period, definition, target, energy_plan, project_id, created_at, archived_at) VALUES
 (11, 'growth', '讀完 12 本書', '2026Q4', '{MARK}定義', 4, 'mid', NULL, {TS}, NULL),
 (12, 'time', '每週讀書', '2026Q4', '', 120, 'low', NULL, {TS}, NULL),
 (13, 'expectation', '空專案上線', '2026Q4', '', 0, 'high', 3, {TS}, NULL),
 (14, 'expectation', '會員系統上線', '2026Q4', '', 0, 'high', 1, {TS}, NULL),
 (15, 'growth', '沒有目標數', '2026Q4', '', 0, 'high', NULL, {TS}, NULL),
 (16, 'expectation', '{MARK}裝修完工', '2026Q4', '', 0, 'high', 4, {TS}, NULL),
 (17, 'growth', '舊目標', '2026Q3', '', 2, 'high', NULL, {TS}, '2026-11-05T09:00+08:00'),
 (18, 'growth', '還沒關聯', '2026Q4', '', 3, 'mid', NULL, {TS}, NULL);
"""
COLS = ("id, project_id, goal_id, title, owner_name, scope, start_date, orig_due, latest_due, status, done_date, "
        "done_when, expected_stars, star_source, version, created_at, updated_at")


def task(tid, title, goal, *, project="1", scope="work", status="done", done="2026-11-07", stars=4):
    done_sql = f"'{done}'" if status == "done" else "NULL"
    goal_sql = "NULL" if goal is None else goal
    return (f"({tid}, {project}, {goal_sql}, '{title}', '{MARK}', '{scope}', '2026-11-01', '2026-11-05', "
            f"'2026-11-05', '{status}', {done_sql}, '{MARK}', {stars}, 'self', 1, {TS}, {TS})")


def fb(tid, actual, energy, overdue):
    return f"({tid}, {tid}, {actual}, '{energy}', 'more', {overdue}, (SELECT min(id) FROM rubrics), {TS})"


TASKS = [
    task(21, "報表查詢改寫", 11, done="2026-11-07", stars=4),
    task(22, "私人看診", 11, project="NULL", scope="private", done="2026-11-09", stars=2),
    task(23, "索引調校 v8", 11, done="2026-11-09", stars=3),
    task(24, "還沒完成", None, status="todo"),          # 專案 1 的未完成任務（expectation 進度）
    task(25, "之後才關聯", None, done="2026-11-08"),     # 有回報、未關聯
    task(31, "裝修估價", 16, project="4", done="2026-11-06"),
    task(41, "舊目標任務", 17, done="2026-11-06"),
    task(51, "讀書時段", 12, done="2026-11-06"),
    task(61, "會員上線準備", 14, done="2026-11-06"),
]
FEEDBACK = [fb(21, 5, "high", 0), fb(22, 3, "low", 2), fb(23, 4, "high", 0), fb(25, 4, "mid", 0),
            fb(31, 3, "mid", 0), fb(41, 3, "mid", 0), fb(51, 3, "mid", 0), fb(61, 3, "mid", 0)]

# 目標 11：母體 21、22、23；linked 3、avg_actual 4.0、avg_expected 3.0、overdue 1、high2 mid0 low1、75%
# 允許名單：3、4.0、3.0、1、2、0、75；標題 12；期間 2026、4；任務標題 8（v8）；完成日 2026、11、9、7
OK_DRAFT = ("【目標】讀完 12 本書（能力成長，2026Q4，預期精力：中）\n\n"
            "【進度】已關聯 3 件完成工作，進度 75%；實際平均 4.0 星，事前預設 3.0 星；逾期 1 件。\n\n"
            "【精力分布】高 2 件、中 0 件、低 1 件。\n\n"
            "【相關工作】\n・索引調校 v8（11/9）\n・報表查詢改寫（11/7）\n\n【判讀】樣本不足，不下判讀。")
OK_FIGURES = [{"key": "linked", "value": 3}, {"key": "avg_actual", "value": 4}, {"key": "avg_expected", "value": 3},
              {"key": "overdue_count", "value": 1}, {"key": "energy.high", "value": 2},
              {"key": "energy.mid", "value": 0}, {"key": "energy.low", "value": 1},
              {"key": "progress_pct", "value": 75}]
OK = {"draft": OK_DRAFT, "figures": OK_FIGURES}
R3_BAD = {"draft": OK_DRAFT + "\n相差 0.7 星", "figures": OK_FIGURES}
# 目標 17（已封存）：母體只有 41 → linked 1、進度 1／2＝50%；允許名單另有期間 2026、3 與完成日 2026、11、6
OK_17 = {"draft": "【進度】已關聯 1 件完成工作，進度 50%。", "figures": [{"key": "linked", "value": 1},
                                                            {"key": "progress_pct", "value": 50}]}


@pytest.fixture
def data(seed):
    seed(BASE)
    seed(f"INSERT INTO tasks ({COLS}) VALUES\n" + ",\n".join(TASKS) + ";\n"
         "INSERT INTO completion_feedback (id, task_id, actual_stars, energy, invest_vs_expected, overdue_days, "
         "rubric_id, created_at) VALUES\n" + ",\n".join(FEEDBACK) + ";")


def draft(client, goal=11, **kw):
    return client.post(f"{API}/goals/{goal}/report/draft", **kw)


def get(client, goal=11):
    return client.get(f"{API}/goals/{goal}/report")


def put(client, text, goal=11, **kw):
    return client.put(f"{API}/goals/{goal}/report/manual", json={"manual_text": text}, **kw)


def ok_body(r):
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == KEYS
    return body


def row(query, goal=11):
    rows = query("SELECT * FROM reports WHERE kind = 'goal' AND goal_id = :g", g=goal)
    assert len(rows) <= 1
    return rows[0] if rows else None


def runs(query):
    return query("SELECT * FROM ai_runs WHERE node_id = 'AI-04' ORDER BY id")


def ai04_calls(ai):
    return [p for n, p in ai.calls if n == "AI-04"]


def generated(client, ai, goal=11, output=None):
    ai.script("AI-04", output or (OK if goal == 11 else OK_17))
    body = ok_body(draft(client, goal))
    assert body["validated"] is True
    return body


# ---------- E1～E5 產生與存檔 ----------

def test_e1_e2_success_response_and_stored_row(client, data, ai, query):
    body = generated(client, ai)
    r = row(query)
    assert body == {"id": r["id"], "goal_id": 11, "ai_status": "ok", "excluded_private": 1, "draft": OK_DRAFT,
                    "validated": True, "manual_text": None, "updated_at": NOW}
    assert (r["ai_draft"], r["ai_status"], r["excluded_private"], r["period_start"]) == (OK_DRAFT, "ok", 1, None)
    assert r["ai_items"] == OK_FIGURES                       # 驗證後的 figures，每項只有 key、value
    assert all(set(f) == {"key", "value"} for f in r["ai_items"])


def test_e3_one_row_per_goal(client, data, ai, query):
    first = generated(client, ai)
    created = row(query)["created_at"]
    ai.script("AI-04", {"draft": OK_DRAFT + "\n補充。", "figures": OK_FIGURES})
    second = ok_body(draft(client))
    assert second["id"] == first["id"] and count(query, "reports") == 1
    assert row(query)["ai_draft"].endswith("補充。") and row(query)["created_at"] == created
    generated(client, ai, goal=17)                           # 不同目標各一列（17 已封存也可產生，E10）
    assert count(query, "reports") == 2


@pytest.mark.parametrize("sql", [
    "INSERT INTO reports (kind, goal_id, excluded_private, created_at, updated_at) VALUES ('goal', 11, 0, now(), now())",
    "INSERT INTO reports (kind, goal_id, excluded_private, created_at, updated_at) VALUES ('goal', NULL, 0, now(), now())",
], ids=["duplicate-goal", "goal-null"])
def test_e4_migration_constraints(client, data, ai, db, sql):
    generated(client, ai)
    with pytest.raises(IntegrityError):
        db.run(lambda c: c.exec_driver_sql(sql))


def test_e4_weekly_rows_unaffected(client, data, ai, query):
    generated(client, ai)
    weekly = client.post(f"{API}/reports/weekly/draft", json={"week_start": "2026-11-09"})
    assert weekly.status_code == 200 and count(query, "reports") == 2


def test_e5_regenerate_keeps_manual_text(client, data, ai, query):
    generated(client, ai)
    ok_body(put(client, "我自己改的版本"))
    generated(client, ai)
    assert row(query)["manual_text"] == "我自己改的版本"


# ---------- E6～E10 失敗、不呼叫 AI、封存 ----------

@pytest.mark.parametrize("script, status", [
    ((AIUnavailable,), "unavailable"),
    ((AIInvalidOutput, AIInvalidOutput, AIInvalidOutput), "invalid_output"),
    ((R3_BAD,), "invalid_output"),
], ids=["unavailable", "invalid", "r3"])
def test_e6_failure_keeps_previous_success_row(client, data, ai, query, script, status):
    generated(client, ai)
    ok_body(put(client, "人工版"))
    before = row(query)
    ai.script("AI-04", *script)
    body = ok_body(draft(client))
    assert body == {"id": before["id"], "goal_id": 11, "ai_status": status, "excluded_private": 1, "draft": None,
                    "validated": False, "manual_text": "人工版", "updated_at": NOW}
    assert row(query) == before


def test_e7_first_failure_creates_row_with_null_ai_fields(client, data, ai, query):
    ai.script("AI-04", AIUnavailable)
    body = ok_body(draft(client))
    r = row(query)
    assert (body["ai_status"], body["validated"], body["draft"]) == ("unavailable", False, None)
    assert (r["ai_draft"], r["ai_items"], r["ai_status"]) == (None, None, "unavailable")
    # E7b：沒有成功草稿的列，GET、PUT 都回 validated=false（不拿 null 跑 R3）
    assert ok_body(get(client))["validated"] is False
    assert ok_body(put(client, "x"))["validated"] is False


def test_e7_failure_on_row_without_success_updates_status(client, data, ai, query):
    ai.script("AI-04", AIUnavailable)
    draft(client)
    ai.script("AI-04", AIInvalidOutput, AIInvalidOutput, AIInvalidOutput)
    ok_body(draft(client))
    assert row(query)["ai_status"] == "invalid_output" and row(query)["ai_draft"] is None


@pytest.mark.parametrize("goal", [18, 16], ids=["linked-0", "private-project-goal"])
def test_e8_e9_no_ai_call(client, data, ai, query, goal):
    body = ok_body(draft(client, goal))
    assert (body["ai_status"], body["validated"], body["draft"]) == ("unavailable", False, None)
    assert ai04_calls(ai) == [] and runs(query) == []
    assert row(query, goal)["ai_status"] == "unavailable"     # 第一次：照失敗規則建列


def test_e8_linked_zero_keeps_previous_success(client, data, ai, query, seed):
    generated(client, ai)
    before = row(query)
    seed("UPDATE tasks SET goal_id = NULL WHERE goal_id = 11;")
    body = ok_body(draft(client))
    assert (body["validated"], body["ai_status"]) == (False, "unavailable")
    assert len(ai04_calls(ai)) == 1                         # 只有第一次產生呼叫過 AI
    assert row(query) == before
    assert ok_body(get(client))["validated"] is False


def test_e9_project_scope_judged_at_send_time(client, data, ai, seed):
    seed("UPDATE projects SET scope = 'work', audience = 'manager' WHERE id = 4;")
    ai.script("AI-04", AIUnavailable)
    draft(client, 16)
    assert [p["goal"]["title"] for p in ai04_calls(ai)] == [f"{MARK}裝修完工"]   # 工作範圍時照送
    seed("UPDATE projects SET scope = 'private', audience = 'none' WHERE id = 4;")
    draft(client, 16)
    assert len(ai04_calls(ai)) == 1                                               # 改回私人：不再送


def test_e10_archived_goal(client, data, ai):
    generated(client, ai, goal=17)
    assert ok_body(get(client, 17))["validated"] is True
    assert ok_body(put(client, "封存也能存", goal=17))["manual_text"] == "封存也能存"


# ---------- E11～E13 讀取與重新對帳 ----------

def test_e11_get_equals_post_and_has_no_side_effect(client, data, ai, query):
    body = generated(client, ai)
    before = {t: count(query, t) for t in ("reports", "ai_runs", "events", "idempotency_keys")}
    assert ok_body(get(client)) == body
    assert {t: count(query, t) for t in before} == before and len(ai04_calls(ai)) == 1


def test_e12_e17_not_found(client, data):
    r = get(client)
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    assert r.json()["error"]["details"] == {"goal_id": 11}
    for resp in (get(client, 999), draft(client, 999), put(client, "x", goal=999)):
        assert resp.status_code == 404 and resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("change, undo", [
    ("UPDATE tasks SET goal_id = 11 WHERE id = 25", "UPDATE tasks SET goal_id = NULL WHERE id = 25"),
    ("UPDATE tasks SET goal_id = NULL WHERE id = 23", "UPDATE tasks SET goal_id = 11 WHERE id = 23"),
    ("UPDATE goals SET title = '讀完 13 本書' WHERE id = 11", "UPDATE goals SET title = '讀完 12 本書' WHERE id = 11"),
    ("UPDATE goals SET target = 5 WHERE id = 11", "UPDATE goals SET target = 4 WHERE id = 11"),
    ("UPDATE tasks SET title = '索引調校' WHERE id = 23", "UPDATE tasks SET title = '索引調校 v8' WHERE id = 23"),
    ("UPDATE completion_feedback SET energy = 'low' WHERE task_id = 21",
     "UPDATE completion_feedback SET energy = 'high' WHERE task_id = 21"),
], ids=["new-link", "unlink", "goal-title", "target", "task-title", "feedback"])
def test_e13_get_and_put_reconcile_against_current_data(client, data, ai, seed, change, undo):
    generated(client, ai)
    seed(change + ";")
    body = ok_body(get(client))
    assert (body["validated"], body["draft"], body["ai_status"]) == (False, None, "ok")
    assert ok_body(put(client, "人工"))["validated"] is False          # E14b：PUT 回應也重跑
    seed(undo + ";")
    assert ok_body(get(client))["validated"] is True


def test_e13_expectation_project_progress_change(client, data, ai, seed):
    # 專案 1 的任務：21、23、24（未完成）、25、41、51、61 → 6／7 完成＝86%（22 是私人單點任務，不在專案內）
    ai.script("AI-04", {"draft": "【進度】進度 86%。", "figures": [{"key": "progress_pct", "value": 86}]})
    assert ok_body(draft(client, 14))["validated"] is True
    seed("UPDATE tasks SET status = 'done', done_date = '2026-11-10' WHERE id = 24;")
    assert ok_body(get(client, 14))["validated"] is False


def test_e13_goal_period_change(client, data, ai, seed):
    """期間裡的數字退出允許名單。2026Q4 的 2026、4 和完成日、avg_actual 撞號，所以用帶 W51 的期間。"""
    seed("UPDATE goals SET period = '2026Q4-W51' WHERE id = 11;")
    generated(client, ai, output={"draft": OK_DRAFT + "\n期間 2026Q4-W51。", "figures": OK_FIGURES})
    seed("UPDATE goals SET period = '2026Q4' WHERE id = 11;")
    assert ok_body(get(client))["validated"] is False


def test_e13_task_created_with_goal_then_completed(client, data, ai, seed):
    generated(client, ai)
    seed(f"INSERT INTO tasks ({COLS}) VALUES {task(26, '建立時就帶目標', 11, status='todo')};")
    assert ok_body(get(client))["validated"] is True           # 未完成：不在母體
    seed("UPDATE tasks SET status = 'done', done_date = '2026-11-10' WHERE id = 26;"
         f"INSERT INTO completion_feedback (id, task_id, actual_stars, energy, invest_vs_expected, overdue_days, "
         f"rubric_id, created_at) VALUES {fb(26, 4, 'mid', 0)};")
    assert ok_body(get(client))["validated"] is False


def test_get_excluded_private_is_stored_value(client, data, ai, seed):
    generated(client, ai)
    seed("UPDATE tasks SET scope = 'private' WHERE id = 21;")
    assert ok_body(get(client))["excluded_private"] == 1


# ---------- E14～E16 人工版 ----------

def test_e14_put_manual(client, data, ai, query):
    generated(client, ai)
    before = row(query)
    for text in ("第一版", "第一版", "", None, "最後一版"):
        body = ok_body(put(client, text))
        assert body["manual_text"] == text
    after = row(query)
    assert after["manual_text"] == "最後一版"
    assert {k: after[k] for k in ("ai_draft", "ai_items", "ai_status", "excluded_private")} == \
        {k: before[k] for k in ("ai_draft", "ai_items", "ai_status", "excluded_private")}


def test_e15_manual_limits(client, data, ai, query, caplog):
    generated(client, ai)
    assert ok_body(put(client, "字" * 20_000))["manual_text"] == "字" * 20_000
    with caplog.at_level("DEBUG"):
        too_long = put(client, MARK + "字" * 20_000)
        nul = put(client, MARK + "\x00")
    assert too_long.status_code == 413 and too_long.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert nul.status_code == 422 and nul.json()["error"]["code"] == "VALIDATION_ERROR"
    assert MARK not in too_long.text + nul.text + caplog.text
    assert row(query)["manual_text"] == "字" * 20_000


@pytest.mark.parametrize("body", [{"manual_text": 3}, {}], ids=["wrong-type", "missing"])
def test_e15_manual_bad_body(client, data, body):
    r = client.put(f"{API}/goals/11/report/manual", json=body)
    assert r.status_code == 422


def test_e16_put_creates_row(client, data, query):
    body = ok_body(put(client, "先寫人工版"))
    r = row(query)
    assert (r["ai_status"], r["ai_draft"], r["ai_items"], r["manual_text"]) == (None, None, None, "先寫人工版")
    assert (body["ai_status"], body["validated"], body["draft"]) == (None, False, None)
    assert ok_body(get(client)) == body


# ---------- E18～E25 其他 ----------

def test_e18_weekly_endpoints_do_not_read_goal_rows(client, data, ai, query):
    generated(client, ai)
    rid = row(query)["id"]
    assert client.get(f"{API}/reports/weekly/{rid}").status_code == 404
    assert client.put(f"{API}/reports/weekly/{rid}/manual", json={"manual_text": "x"}).status_code == 404


def test_e19_no_idempotency_cache_for_report_writes(client, data, ai, query):
    ai.script("AI-04", OK, OK)
    h = {"Idempotency-Key": "gr-1"}
    ok_body(draft(client, headers=h))
    ok_body(draft(client, headers=h))
    ok_body(put(client, "人工", headers={"Idempotency-Key": "gr-2"}))
    ok_body(put(client, "人工", headers={"Idempotency-Key": "gr-2"}))
    assert len(ai04_calls(ai)) == 2 and count(query, "idempotency_keys") == 0


def test_e19b_other_goal_endpoints_still_cached(client, data, ai, query):
    h = {"Idempotency-Key": "g-create"}
    body = {"type": "growth", "title": "新目標", "period": "2026Q4", "energy_plan": "mid"}
    first = client.post(f"{API}/goals", json=body, headers=h)
    assert client.post(f"{API}/goals", json=body, headers=h).json() == first.json()
    assert query("SELECT count(*) AS n FROM goals WHERE title = '新目標'")[0]["n"] == 1
    gid = first.json()["id"]
    for method, path, payload in (("PATCH", f"/goals/{gid}", {"title": "改名"}), ("POST", f"/goals/{gid}/archive", None)):
        h = {"Idempotency-Key": f"k-{method}"}
        a = client.request(method, f"{API}{path}", json=payload, headers=h)
        b = client.request(method, f"{API}{path}", json=payload, headers=h)
        assert a.json() == b.json()
    assert count(query, "idempotency_keys") == 3


def test_e20_e_no_feedback_no_events(client, data, ai, query):
    before = {t: count(query, t) for t in ("ai_feedback", "events")}
    generated(client, ai)
    put(client, "人工")
    assert {t: count(query, t) for t in before} == before


def test_e21_export(client, data, ai):
    generated(client, ai)
    put(client, "人工版")
    goal_rows = [r for r in client.post(f"{API}/export").json()["tables"]["reports"] if r["kind"] == "goal"]
    assert len(goal_rows) == 1
    assert "ai_draft" not in goal_rows[0]
    assert goal_rows[0]["manual_text"] == "人工版" and goal_rows[0]["ai_items"] == OK_FIGURES


def test_e23_payload_via_endpoint(client, data, ai):
    generated(client, ai)
    [payload] = ai04_calls(ai)
    assert payload["goal"] == {"type": "growth", "title": "讀完 12 本書", "period": "2026Q4", "energy_plan": "mid"}
    assert payload["stats"] == {"linked": 3, "avg_actual": 4.0, "avg_expected": 3.0, "overdue_count": 1,
                                "energy": {"high": 2, "mid": 0, "low": 1}, "progress_pct": 75, "judgement": None}
    assert payload["tasks"] == [{"task_id": 23, "title": "索引調校 v8", "done_date": "2026-11-09"},
                                {"task_id": 21, "title": "報表查詢改寫", "done_date": "2026-11-07"}]
    assert MARK not in json.dumps(payload, ensure_ascii=False) and "私人看診" not in json.dumps(payload, ensure_ascii=False)


def test_e24_no_task_limit(client, data, ai, seed):
    ids = range(100, 125)
    seed(f"INSERT INTO tasks ({COLS}) VALUES " + ",".join(task(i, f"工作{i}", 15, done="2026-11-03") for i in ids)
         + "; INSERT INTO completion_feedback (id, task_id, actual_stars, energy, invest_vs_expected, overdue_days, "
         "rubric_id, created_at) VALUES " + ",".join(fb(i, 3, "mid", 0) for i in ids) + ";")
    ai.script("AI-04", AIUnavailable)
    draft(client, 15)
    assert len(ai04_calls(ai)[0]["tasks"]) == 25


@pytest.mark.parametrize("goal", [12, 15, 13], ids=["time", "target-0", "empty-project"])
def test_progress_pct_null_types_via_endpoint(client, data, ai, seed, goal):
    if goal in (15, 13):
        seed(f"UPDATE tasks SET goal_id = {goal} WHERE id = 25;")
    ai.script("AI-04", AIUnavailable)
    draft(client, goal)
    assert ai04_calls(ai)[0]["stats"]["progress_pct"] is None


def test_e25_logs_never_carry_content(client, data, ai, caplog):
    with caplog.at_level("DEBUG"):
        generated(client, ai)
        put(client, MARK + "人工版")
        ai.script("AI-04", RuntimeError(MARK + "報表查詢改寫"), {"draft": MARK, "figures": [{"key": MARK, "value": 1}]},
                  R3_BAD)
        draft(client)
    for text in (MARK, OK_DRAFT[:10], "報表查詢改寫", "讀完 12 本書", "相差 0.7"):
        assert text not in caplog.text


def test_requires_token(app, data):
    from fastapi.testclient import TestClient
    bare = TestClient(app)
    for method, path in (("POST", "/goals/11/report/draft"), ("GET", "/goals/11/report"),
                         ("PUT", "/goals/11/report/manual")):
        assert bare.request(method, f"{API}{path}", json={"manual_text": "x"}).status_code == 401


def test_openapi_lists_endpoints(client):
    paths = client.get(f"{API}/openapi.json").json()["paths"]
    assert "post" in paths["/api/v1/goals/{goal_id}/report/draft"]
    assert "get" in paths["/api/v1/goals/{goal_id}/report"]
    assert "put" in paths["/api/v1/goals/{goal_id}/report/manual"]


# ---------- T 系列 重試與紀錄（5.3a「同 AI-05」） ----------

def test_t1_success_one_run(client, data, ai, query):
    generated(client, ai)
    [run] = runs(query)
    assert (run["status"], run["attempt"], run["error"], run["raw_output"], run["job_id"]) == ("ok", 1, None, None, None)
    assert run["latency_ms"] is not None


@pytest.mark.parametrize("script, statuses, errors, final", [
    ((AIUnavailable,), ["error"], ["AIUnavailable"], "unavailable"),
    ((AIInvalidOutput,) * 3, ["invalid_output"] * 3, ["AIInvalidOutput"] * 3, "invalid_output"),
    ((AITimeout, AIInvalidOutput, OK), ["timeout", "invalid_output", "ok"], ["AITimeout", "AIInvalidOutput", None], "ok"),
    ((R3_BAD,), ["invalid_output"], ["R3_MISMATCH"], "invalid_output"),
    ((AITimeout, AITimeout, AIInvalidOutput), ["timeout", "timeout", "invalid_output"],
     ["AITimeout", "AITimeout", "AIInvalidOutput"], "invalid_output"),
    ((AIInvalidOutput, AIInvalidOutput, AITimeout), ["invalid_output", "invalid_output", "timeout"],
     ["AIInvalidOutput", "AIInvalidOutput", "AITimeout"], "unavailable"),
    (({"draft": "  ", "figures": []}, {"draft": "x\x00", "figures": []}, OK),
     ["invalid_output", "invalid_output", "ok"], ["AIInvalidOutput", "AIInvalidOutput", None], "ok"),
    ((AIInvalidOutput, R3_BAD), ["invalid_output", "invalid_output"], ["AIInvalidOutput", "R3_MISMATCH"],
     "invalid_output"),
    ((AITimeout, R3_BAD), ["timeout", "invalid_output"], ["AITimeout", "R3_MISMATCH"], "invalid_output"),
    ((AIInvalidOutput, AIUnavailable), ["invalid_output", "error"], ["AIInvalidOutput", "AIUnavailable"],
     "unavailable"),
    ((RuntimeError("x"), OK), ["error", "ok"], ["RuntimeError", None], "ok"),
], ids=["T2-unavailable", "T3-invalid-x3", "T4-timeout-invalid-ok", "T5-r3-stops", "T6-last-invalid",
        "T6-last-timeout", "T12-caller-format-errors-retry", "T13a-invalid-r3", "T13b-timeout-r3",
        "T13c-invalid-unavailable", "T9-runtime-error-retries"])
def test_t_retry_sequences(client, data, ai, query, script, statuses, errors, final):
    ai.script("AI-04", *script)
    assert ok_body(draft(client))["ai_status"] == final
    rs = runs(query)
    assert [r["status"] for r in rs] == statuses and [r["error"] for r in rs] == errors
    assert [r["attempt"] for r in rs] == list(range(1, len(statuses) + 1))
    assert all(r["raw_output"] is None and r["latency_ms"] is not None for r in rs)


def test_t14_rejected_draft_not_stored(client, data, ai, query):
    bad = {"draft": MARK + OK_DRAFT, "figures": [{"key": "linked", "value": 99}]}
    ai.script("AI-04", bad)
    body = ok_body(draft(client))
    assert body["draft"] is None
    assert MARK not in json.dumps(runs(query), ensure_ascii=False, default=str)
    assert MARK not in json.dumps(row(query), ensure_ascii=False, default=str)
