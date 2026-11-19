"""Phase 9 第三片：AI-03 目標關聯建議與回饋（todo 9.7；spec 5.3、5.3a〈AI-03〉、5.13；FR-GOL-03、AC-47、AC-50）。

Dev-A 依 DA-27 暫代撰寫；只經 HTTP、SQL 種子與 FakeAIClient 操作，不讀實作。
測試清單與子代理審查紀錄：.scratch/phase9-ai03/testlist-9.7.md。

- S1～S2 成功回應、payload 鍵集合與內容（只送允許的欄位）。
- S4～S7 目標只送未封存；任務只送工作範圍、待關聯、含封存專案；最多 20 筆、完成日由新到舊。
- S8～S9 沒有目標或沒有可送任務時不呼叫 AI。
- S10～S12 輸出驗證：先查結構（任一項不合整次 invalid_output），再丟不在 payload 的項目，最後同一任務留第一項。
- S13～S15 重試、最終狀態、ai_runs 紀錄（status 細分、latency、raw_output、error 只放類別）。
- S16～S18 log 不洩漏、建議不存檔、冪等重送不再呼叫 AI。
- F1～F11 回饋：accepted／changed、detail 只含 id、ai_run_id 檢查與先後、清除後不寫、去重、失敗不寫、私人任務不寫。
- P1 清除（保存期限、全部刪除）；A1 token。
"""

import json

import pytest
from fastapi.testclient import TestClient

from app import scheduler
from app.ai.client import AIInvalidOutput, AITimeout, AIUnavailable
from tests.acceptance.helpers import API, count

TS = "'2026-11-01T09:00+08:00'"
DEFMARK = "定義不可外送"
BASE = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at, archived_at) VALUES
 (1, '會員系統', 'work', 'manager', {TS}, {TS}, NULL),
 (2, '舊專案', 'work', 'manager', {TS}, {TS}, '2026-11-05T09:00+08:00');
INSERT INTO goals (id, type, title, period, definition, target, energy_plan, project_id, created_at, archived_at) VALUES
 (11, 'growth', '學會 SQL 視窗函式', '2026Q4', '{DEFMARK}', 3, 'mid', NULL, {TS}, NULL),
 (12, 'time', '每週留 2 小時讀書', '2026Q4', '', 120, 'low', NULL, {TS}, NULL),
 (13, 'expectation', '會員系統準時上線', '2026Q4', '', 0, 'high', 1, {TS}, NULL),
 (14, 'growth', '舊目標', '2026Q3', '', 2, 'high', NULL, {TS}, '2026-11-05T09:00+08:00');
"""
TASK_COLS = ("id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, status, done_date, "
             "done_when, expected_stars, star_source, version, created_at, updated_at")


def task_sql(tid, title, *, project="1", scope="work", owner="我", status="done", done="2026-11-07", version=1):
    done_sql = f"'{done}'" if status == "done" else "NULL"
    return (f"({tid}, {project}, '{title}', '{owner}', '{scope}', '2026-11-01', '2026-11-05', '2026-11-05', "
            f"'{status}', {done_sql}, '完成條件不可外送', 4, 'self', {version}, {TS}, {TS})")


def fb_sql(tid):
    return f"({tid}, {tid}, 5, 'high', 'more', 3, (SELECT min(id) FROM rubrics), {TS})"


def seed_tasks(seed, tasks, feedback_ids):
    sql = f"INSERT INTO tasks ({TASK_COLS}) VALUES\n" + ",\n".join(tasks) + ";\n"
    if feedback_ids:
        sql += ("INSERT INTO completion_feedback (id, task_id, actual_stars, energy, invest_vs_expected, overdue_days, "
                "rubric_id, created_at) VALUES\n" + ",\n".join(fb_sql(t) for t in feedback_ids) + ";\n")
    seed(sql)


TASKS = [
    task_sql(21, "報表查詢改寫", done="2026-11-07", version=2),
    task_sql(22, "看牙醫", project="NULL", scope="private", done="2026-11-09"),     # 私人：不送
    task_sql(23, "舊專案收尾", project="2", owner="阿德", done="2026-11-06"),          # 封存專案底下：照送
    task_sql(24, "沒有回報", done="2026-11-08"),                                       # 沒有回報：不送
    task_sql(25, "未完成", status="todo"),                                             # 未完成：不送
    task_sql(26, "已決定過", done="2026-11-08"),                                       # 做過決定：不送
]
DECIDED = f"""INSERT INTO events (ts, task_id, task_title, mine, project_id, kind, field, from_value, to_value, origin)
VALUES ({TS}, 26, '已決定過', true, 1, 'goal', 'goal_id', NULL, NULL, 'manual');"""


@pytest.fixture
def data(seed):
    seed(BASE)
    seed_tasks(seed, TASKS, [21, 22, 23, 26])
    seed(DECIDED)


def ok_output(*items):
    return {"items": [{"task_id": t, "goal_id": g, "reason": r} for t, g, r in items]}


def suggest(client, **kw):
    r = client.post(f"{API}/goal-links/suggest", **kw)
    assert r.status_code == 200, r.text
    return r.json()


def runs(query):
    return query("SELECT * FROM ai_runs WHERE node_id = 'AI-03' ORDER BY id")


def ai03_payloads(ai):
    return [p for n, p in ai.calls if n == "AI-03"]


def link(client, task_id, goal_id, version, **extra):
    return client.post(f"{API}/goal-links",
                       json={"task_id": task_id, "goal_id": goal_id, "expected_version": version} | extra)


def feedback_rows(query):
    return query("SELECT * FROM ai_feedback WHERE node_id = 'AI-03' ORDER BY id")


# ---------- S1～S7：成功、payload ----------

def test_s1_s2_ok_response_and_exact_payload(client, data, ai, query):
    ai.script("AI-03", ok_output((21, 11, "任務內容與 SQL 學習相關"), (23, None, "沒有相關目標")))
    body = suggest(client)
    run = runs(query)
    assert len(run) == 1 and run[0]["status"] == "ok"
    assert body == {"ai_status": "ok", "ai_run_id": run[0]["id"], "items": [
        {"task_id": 21, "goal_id": 11, "reason": "任務內容與 SQL 學習相關"},
        {"task_id": 23, "goal_id": None, "reason": "沒有相關目標"}]}
    assert ai03_payloads(ai) == [{
        "goals": [{"goal_id": 11, "type": "growth", "title": "學會 SQL 視窗函式", "period": "2026Q4"},
                  {"goal_id": 12, "type": "time", "title": "每週留 2 小時讀書", "period": "2026Q4"},
                  {"goal_id": 13, "type": "expectation", "title": "會員系統準時上線", "period": "2026Q4"}],
        "tasks": [{"task_id": 21, "title": "報表查詢改寫", "done_date": "2026-11-07"},
                  {"task_id": 23, "title": "舊專案收尾", "done_date": "2026-11-06"}],
    }]


def test_s3_payload_carries_no_forbidden_values(client, data, ai):
    ai.script("AI-03", ok_output())
    suggest(client)
    sent = json.dumps(ai03_payloads(ai), ensure_ascii=False)
    for forbidden in (DEFMARK, "完成條件不可外送", "阿德", "看牙醫", "會員系統\"", "舊專案\"", "energy", "stars",
                      "overdue", "invest", "project_id", "owner", "target"):
        assert forbidden not in sent, forbidden


def test_s7_at_most_20_newest_work_tasks(client, seed, ai):
    seed(BASE)
    ids = list(range(100, 123))                            # 23 筆；完成日 11-01～11-12，同日的比 id
    seed_tasks(seed, [task_sql(t, f"任務{t}", done=f"2026-11-{(t - 100) // 2 + 1:02d}") for t in ids], ids)
    ai.script("AI-03", ok_output())
    suggest(client)
    sent = [t["task_id"] for t in ai03_payloads(ai)[0]["tasks"]]
    expected = sorted(ids, key=lambda t: ((t - 100) // 2, t), reverse=True)[:20]
    assert sent == expected and len(sent) == 20


@pytest.mark.parametrize("extra_sql", [
    "UPDATE goals SET archived_at = '2026-11-05T09:00+08:00';",                         # 沒有未封存目標
    "DELETE FROM completion_feedback WHERE task_id IN (21, 23);",                        # 只剩私人任務
], ids=["no-active-goal", "no-work-task"])
def test_s8_s9_nothing_to_send_skips_ai(client, data, seed, ai, query, extra_sql):
    seed(extra_sql)
    assert suggest(client) == {"ai_status": "unavailable", "ai_run_id": None, "items": []}
    assert ai03_payloads(ai) == [] and runs(query) == []


# ---------- S10～S12：輸出驗證 ----------

def test_s10_s11_filtering_and_dedup(client, data, ai):
    ai.script("AI-03", ok_output(
        (999, 11, "不在 payload 的任務"),
        (21, 999, "不在 payload 的目標"),        # 先丟掉，所以下一項才是 21 的第一項
        (21, 12, "第一項"),
        (21, 11, "重複，丟棄"),
        (22, 11, "私人任務，丟棄"),
        (21, 14, "封存目標，丟棄"),
        (23, None, "沒有合適目標"),
    ))
    assert suggest(client)["items"] == [{"task_id": 21, "goal_id": 12, "reason": "第一項"},
                                        {"task_id": 23, "goal_id": None, "reason": "沒有合適目標"}]


def test_s10_extra_keys_are_dropped(client, data, ai):
    ai.script("AI-03", {"items": [{"task_id": 21, "goal_id": 11, "reason": "r", "score": 9}], "note": "x"})
    assert suggest(client)["items"] == [{"task_id": 21, "goal_id": 11, "reason": "r"}]


def test_s11_empty_reason_is_allowed(client, data, ai):
    ai.script("AI-03", ok_output((21, 11, "")))
    assert suggest(client)["ai_status"] == "ok"


BAD = [
    "not a dict", {"items": "x"}, {}, {"items": [1]},
    {"items": [{"task_id": 21, "goal_id": 11}]},
    {"items": [{"task_id": "21", "goal_id": 11, "reason": "r"}]},
    {"items": [{"task_id": True, "goal_id": 11, "reason": "r"}]},
    {"items": [{"task_id": 21, "goal_id": "11", "reason": "r"}]},
    {"items": [{"task_id": 21, "goal_id": 2.0, "reason": "r"}]},
    {"items": [{"task_id": 21, "goal_id": False, "reason": "r"}]},
    {"items": [{"task_id": 21, "goal_id": 11, "reason": None}]},
    {"items": [{"task_id": 21, "goal_id": 11, "reason": "字" * 201}]},
    {"items": [{"task_id": 21, "goal_id": 11, "reason": "含\x00字元"}]},
    {"items": [{"task_id": 21, "goal_id": 11, "reason": "ok"}, {"task_id": 999, "goal_id": 11, "reason": "字" * 201}]},
]


@pytest.mark.parametrize("bad", BAD, ids=[f"bad{i}" for i in range(len(BAD))])
def test_s12_malformed_output_is_invalid_after_three_tries(client, data, ai, query, bad):
    ai.script("AI-03", bad, bad, bad)
    assert suggest(client) == {"ai_status": "invalid_output", "ai_run_id": None, "items": []}
    assert [r["status"] for r in runs(query)] == ["invalid_output"] * 3


def test_s12_reason_of_200_chars_is_ok(client, data, ai):
    ai.script("AI-03", ok_output((21, 11, "字" * 200)))
    assert suggest(client)["ai_status"] == "ok"


# ---------- S13～S15：重試與紀錄 ----------

def test_s13_retry_then_ok_uses_last_run(client, data, ai, query):
    ai.script("AI-03", AITimeout, ok_output((21, 11, "r")))
    body = suggest(client)
    rows = runs(query)
    assert [(r["attempt"], r["status"]) for r in rows] == [(1, "timeout"), (2, "ok")]
    assert body["ai_status"] == "ok" and body["ai_run_id"] == rows[1]["id"]


@pytest.mark.parametrize("script, statuses, final", [
    ([AIUnavailable], ["error"], "unavailable"),
    ([{"items": "x"}, {"items": "x"}, AITimeout], ["invalid_output", "invalid_output", "timeout"], "unavailable"),
    ([AITimeout, AITimeout, {"items": "x"}], ["timeout", "timeout", "invalid_output"], "invalid_output"),
    ([{"items": "x"}, AIUnavailable], ["invalid_output", "error"], "unavailable"),
    ([RuntimeError("boom"), AIInvalidOutput, ValueError("x")], ["error", "invalid_output", "error"], "unavailable"),
], ids=["unavailable-stops", "last-timeout", "last-invalid", "invalid-then-unavailable", "any-exception"])
def test_s13_final_status_follows_last_attempt(client, data, ai, query, script, statuses, final):
    ai.script("AI-03", *script)
    assert suggest(client) == {"ai_status": final, "ai_run_id": None, "items": []}
    assert [r["status"] for r in runs(query)] == statuses


def test_s15_runs_record_class_names_latency_and_raw_output(client, data, ai, query):
    bad = {"items": [{"task_id": 21, "goal_id": "11", "reason": "格式錯"}]}
    ai.script("AI-03", RuntimeError("secret 報表查詢改寫"), bad, ok_output((21, 11, "r"), (999, 11, "丟棄")))
    suggest(client)
    first, second, third = runs(query)
    assert (first["error"], first["raw_output"]) == ("RuntimeError", None)
    assert json.loads(second["raw_output"]) == bad and second["error"] == "AIInvalidOutput"
    # status='ok' 那一列存驗證後的建議，和回應一致，供回饋比對（spec 5.13）
    assert json.loads(third["raw_output"]) == {"items": [{"task_id": 21, "goal_id": 11, "reason": "r"}]}
    assert all(r["latency_ms"] is not None for r in (first, second, third))


def test_s16_logs_do_not_leak_titles_or_reason(client, data, ai, caplog):
    ai.script("AI-03", RuntimeError("報表查詢改寫"), {"items": [{"task_id": 21, "goal_id": "x", "reason": "原因原文"}]},
              AITimeout)
    with caplog.at_level("DEBUG"):
        suggest(client)
    for text in ("報表查詢改寫", "學會 SQL 視窗函式", "原因原文", "舊專案收尾"):
        assert text not in caplog.text


def test_s17_suggest_writes_nothing_but_ai_runs(client, data, ai, query):
    before = {t: count(query, t) for t in ("events", "ai_feedback", "tasks")}
    versions = query("SELECT id, goal_id, version FROM tasks ORDER BY id")
    ai.script("AI-03", ok_output((21, 11, "r")))
    suggest(client)
    assert {t: count(query, t) for t in before} == before
    assert query("SELECT id, goal_id, version FROM tasks ORDER BY id") == versions


def test_s18_idempotent_resend_returns_first_result_without_calling_ai(client, data, ai):
    ai.script("AI-03", ok_output((21, 11, "r")))
    first = suggest(client, headers={"Idempotency-Key": "ai03-1"})
    assert suggest(client, headers={"Idempotency-Key": "ai03-1"}) == first
    assert len(ai03_payloads(ai)) == 1


def test_s14_link_without_ai_still_works_when_ai_down(client, data, ai, query):
    ai.available = False
    assert suggest(client)["ai_status"] == "unavailable"
    assert link(client, 21, 11, 2).status_code == 200            # 非 AI 功能照常（AC-50）
    assert feedback_rows(query) == []


# ---------- F1～F11：回饋 ----------

@pytest.fixture
def run_id(client, data, ai):
    ai.script("AI-03", ok_output((21, 11, "r21"), (23, None, "r23")))
    return suggest(client)["ai_run_id"]


def test_f1_ac47_changed_goal_writes_changed(client, run_id, query):
    r = link(client, 21, 12, 2, ai_run_id=run_id)
    assert r.status_code == 200 and query("SELECT goal_id FROM tasks WHERE id = 21")[0]["goal_id"] == 12
    fb = feedback_rows(query)
    assert len(fb) == 1
    assert (fb[0]["target_type"], fb[0]["target_id"], fb[0]["outcome"]) == ("goal_link", r.json()["event"]["id"], "changed")
    assert fb[0]["detail"] == {"ai_run_id": run_id, "task_id": 21, "ai": 11, "final": 12}


@pytest.mark.parametrize("task_id, goal_id, version, outcome", [
    (21, 11, 2, "accepted"),
    (21, None, 2, "changed"),
    (23, None, 1, "accepted"),
    (23, 11, 1, "changed"),
], ids=["same-goal", "suggest-goal-pick-none", "suggest-none-pick-none", "suggest-none-pick-goal"])
def test_f2_f3_outcomes(client, run_id, query, task_id, goal_id, version, outcome):
    assert link(client, task_id, goal_id, version, ai_run_id=run_id).status_code == 200
    assert [f["outcome"] for f in feedback_rows(query)] == [outcome]


def test_f4_detail_holds_only_ids(client, run_id, query):
    link(client, 21, 12, 2, ai_run_id=run_id)
    detail = feedback_rows(query)[0]["detail"]
    assert all(v is None or (isinstance(v, int) and not isinstance(v, bool)) for v in detail.values())
    assert "r21" not in json.dumps(detail, ensure_ascii=False)


@pytest.mark.parametrize("bad_run_sql", [
    None,                                                                                    # 不存在
    "INSERT INTO ai_runs (id, node_id, status, attempt, raw_output, created_at) VALUES "
    "(900, 'AI-07', 'ok', 1, '{\"items\": []}', '2026-11-11T09:00+08:00');",              # 別的節點
    "INSERT INTO ai_runs (id, node_id, status, attempt, raw_output, created_at) VALUES "
    "(900, 'AI-03', 'invalid_output', 1, '{\"items\": []}', '2026-11-11T09:00+08:00');",   # 不是 ok
], ids=["missing", "other-node", "not-ok"])
def test_f5_bad_ai_run_id_rejects_link(client, data, seed, query, bad_run_sql):
    if bad_run_sql:
        seed(bad_run_sql)
    before = count(query, "events")
    r = link(client, 21, 11, 2, ai_run_id=900)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert r.json()["error"]["details"]["fields"] == ["ai_run_id"]
    assert count(query, "events") == before and feedback_rows(query) == []
    assert query("SELECT goal_id, version FROM tasks WHERE id = 21")[0] == {"goal_id": None, "version": 2}


def test_f5_task_errors_come_before_ai_run_id(client, data):
    assert link(client, 21, 11, 9, ai_run_id=900).json()["error"]["code"] == "STALE_VERSION"
    assert link(client, 999, 11, 1, ai_run_id=900).json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("bad", ["1", True, 1.5], ids=["str", "bool", "float"])
def test_f6_ai_run_id_must_be_int(client, run_id, query, bad):
    r = link(client, 21, 11, 2, ai_run_id=bad)
    assert r.status_code == 422 and feedback_rows(query) == []


def test_f6_null_ai_run_id_is_same_as_absent(client, run_id, query):
    assert link(client, 21, 11, 2, ai_run_id=None).status_code == 200
    assert feedback_rows(query) == []


def test_f6_error_details_do_not_echo_content(client, run_id):
    r = link(client, 21, 999, 2, ai_run_id=run_id)
    assert r.status_code == 422 and "r21" not in r.text and "報表查詢改寫" not in r.text


def test_f7_purged_raw_output_links_without_feedback(client, run_id, query):
    assert client.post(f"{API}/sources/purge", json={"confirm": True}).status_code == 200
    assert link(client, 21, 12, 2, ai_run_id=run_id).status_code == 200
    assert feedback_rows(query) == []


def test_f8_task_not_in_suggestion_writes_no_feedback(client, run_id, seed, query):
    seed_tasks(seed, [task_sql(27, "建議之後才完成", done="2026-11-10")], [27])
    assert link(client, 27, 11, 1, ai_run_id=run_id).status_code == 200
    assert feedback_rows(query) == []


def test_f8_private_task_with_ai_run_id_writes_no_feedback(client, run_id, query):
    assert link(client, 22, 11, 1, ai_run_id=run_id).status_code == 200
    assert feedback_rows(query) == []


def test_f9_one_feedback_per_run_and_task(client, run_id, ai, query):
    assert link(client, 21, 12, 2, ai_run_id=run_id).status_code == 200
    assert link(client, 21, 11, 3, ai_run_id=run_id).status_code == 200      # 同一 run 改選：不再寫
    assert len(feedback_rows(query)) == 1
    ai.script("AI-03", ok_output((23, 12, "r")))
    second = suggest(client)["ai_run_id"]                                       # 21 已做過決定，不再送
    assert link(client, 23, 12, 1, ai_run_id=second).status_code == 200      # 不同 run 各寫一筆
    assert [f["detail"]["task_id"] for f in feedback_rows(query)] == [21, 23]


def test_f9_feedback_only_for_first_decision(client, run_id, query):
    # code-review：改選時才帶 ai_run_id（或帶舊的 run）不算對建議的回應，不寫回饋（spec 5.13）
    assert link(client, 21, 12, 2).status_code == 200                           # 第一次決定沒帶 ai_run_id
    assert link(client, 21, 11, 3, ai_run_id=run_id).status_code == 200      # 改選才帶：不寫
    assert feedback_rows(query) == []


@pytest.mark.parametrize("args, code", [
    ((21, 11, 1), "STALE_VERSION"),
    ((21, 14, 2), "VALIDATION_ERROR"),                 # 封存目標
], ids=["stale", "archived-goal"])
def test_f10_failed_link_writes_no_feedback(client, run_id, query, args, code):
    r = link(client, *args, ai_run_id=run_id)
    assert r.json()["error"]["code"] == code and feedback_rows(query) == []


def test_f10_no_change_writes_no_feedback(client, run_id, query):
    assert link(client, 21, 11, 2).status_code == 200                           # 先不帶 ai_run_id 關聯
    assert link(client, 21, 11, 3, ai_run_id=run_id).json()["error"]["code"] == "NO_CHANGE"
    assert feedback_rows(query) == []


# ---------- P1：清除；A1：認證 ----------

def test_p1_retention_purge_clears_ai03_raw_output(client, run_id, seed, db, query):
    seed("UPDATE ai_runs SET created_at = '2026-09-01T09:00+08:00' WHERE node_id = 'AI-03';")
    scheduler.run_once(db)
    assert [r["raw_output"] for r in runs(query)] == [None]


def test_a1_suggest_requires_token(app, data, ai, query):
    with TestClient(app) as anon:
        r = anon.post(f"{API}/goal-links/suggest")
    assert r.status_code == 401 and ai03_payloads(ai) == [] and runs(query) == []
