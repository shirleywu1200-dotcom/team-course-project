"""Phase 9 第一片：完成回報、待補清單、伺服器今天（todo 9.1、9.2、9.4；spec 3.12、5.12、6.5；#47 A1～A6）。

Dev-A 依 DA-27 暫代撰寫；只經 HTTP 與 SQL 種子操作，不讀實作。
9.4 的測試（標 FR-AI-06）屬 FR-AI-06 防回歸，QC 帳號建立後移交 QC 持有，不得刪除或放寬。
測試清單與獨立審查紀錄：PR 說明。

日期設計：FixedClock 的今天是 2026-11-11。逾期天數的種子刻意讓三種錯誤公式（以今天算、以最新預計日算、
不取 max）得到不同答案，避免測試空轉。
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.clock import FixedClock, set_clock
from tests.acceptance.helpers import API, count, ingest

TS = "'2026-11-01T09:00+08:00'"
MARK54 = "ZXQ9FB"

# 專案：1 工作、2 私人、4 已封存（工作）
# 任務（id 越大 done_date 越早的有好幾筆，排序測試才不會靠自然順序通過）：
#   21 我、done 11-07、orig 11-05、latest 11-10 → 逾期 2（以 latest 算為 0、以今天算為 6）
#   22 阿德、done 11-06、orig 11-09 → 提前完成，0
#   23 單點、done 11-03、orig 11-03 → 當天，0
#   24 私人專案、done 11-08、orig 11-06 → 2
#   25 封存專案、done 11-06、orig 11-04 → 2（與 22 同日，驗 task_id 次排序）
#   26 done 11-05 早於開始日 11-10、orig 11-12 → 0（spec 6.5）
#   27 todo、28 doing
#   29 done 11-02、expected_stars 4、star_source ai_accepted → 0
SEED = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at, archived_at) VALUES
 (1, '會員系統', 'work', 'manager', {TS}, {TS}, NULL),
 (2, '家庭旅行', 'private', 'none', {TS}, {TS}, NULL),
 (4, '舊專案', 'work', 'manager', {TS}, {TS}, '2026-11-09T09:00+08:00');
INSERT INTO goals (id, type, title, period, energy_plan, created_at) VALUES
 (1, 'growth', '學 SQL', '2026Q4', 'mid', {TS});
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, status, done_date,
                   expected_stars, star_source, created_at, updated_at) VALUES
 (21, 1, '畫面規格', '我', 'work', '2026-11-01', '2026-11-05', '2026-11-10', 'done', '2026-11-07', 3, 'self', {TS}, {TS}),
 (22, 1, '介面定義', '阿德', 'work', '2026-11-01', '2026-11-09', '2026-11-09', 'done', '2026-11-06', 3, 'self', {TS}, {TS}),
 (23, NULL, '報帳', '我', 'work', '2026-11-01', '2026-11-03', '2026-11-03', 'done', '2026-11-03', 3, 'self', {TS}, {TS}),
 (24, 2, '訂機票', '我', 'private', '2026-11-01', '2026-11-06', '2026-11-06', 'done', '2026-11-08', 3, 'self', {TS}, {TS}),
 (25, 4, '結案報告', '我', 'work', '2026-11-01', '2026-11-04', '2026-11-04', 'done', '2026-11-06', 3, 'self', {TS}, {TS}),
 (26, 1, '提早交付', '我', 'work', '2026-11-10', '2026-11-12', '2026-11-12', 'done', '2026-11-05', 3, 'self', {TS}, {TS}),
 (27, 1, '測試環境', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-20', 'todo', NULL, 3, 'self', {TS}, {TS}),
 (28, 1, '整合測試', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-20', 'doing', NULL, 3, 'self', {TS}, {TS}),
 (29, 1, '需求訪談', '我', 'work', '2026-11-01', '2026-11-02', '2026-11-02', 'done', '2026-11-02', 4, 'ai_accepted',
  {TS}, {TS});
"""

PENDING_KEYS = {"task_id", "title", "owner", "project_id", "done_date", "orig_due", "overdue_days", "expected_stars",
                "star_source"}
FEEDBACK_KEYS = {"id", "task_id", "actual_stars", "energy", "invest_vs_expected", "overdue_days", "rubric_id",
                 "created_at"}
NOW = "2026-11-11T10:00:00+08:00"


def rubric_id(query):
    return query("SELECT id FROM rubrics ORDER BY version DESC LIMIT 1")[0]["id"]


def body(query, **kw):
    return {"actual_stars": 4, "energy": "mid", "invest_vs_expected": "as_expected", "rubric_id": rubric_id(query)} | kw


def put(client, task_id, payload, **kw):
    return client.put(f"{API}/tasks/{task_id}/feedback", json=payload, **kw)


def task_row(query, task_id):
    return query("SELECT * FROM tasks WHERE id = :t", t=task_id)[0]


def pending(client):
    r = client.get(f"{API}/feedback/pending")
    assert r.status_code == 200, r.text
    return r.json()


def assert_validation(r, fields):
    assert r.status_code == 422, r.text
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert sorted(err["details"]["fields"]) == sorted(fields)


# ---------- F1～F4：儲存回報 ----------

def test_f1_save_feedback_returns_201_with_server_values(client, seed, query):
    seed(SEED)
    r = put(client, 21, body(query))
    assert r.status_code == 201, r.text
    out = r.json()
    assert set(out) == {"feedback", "event"}
    fb = out["feedback"]
    assert set(fb) == FEEDBACK_KEYS
    assert (fb["task_id"], fb["actual_stars"], fb["energy"], fb["invest_vs_expected"], fb["rubric_id"]) == \
        (21, 4, "mid", "as_expected", rubric_id(query))
    assert fb["created_at"] == NOW
    assert query("SELECT task_id, actual_stars, energy, rubric_id FROM completion_feedback") == \
        [{"task_id": 21, "actual_stars": 4, "energy": "mid", "rubric_id": rubric_id(query)}]


@pytest.mark.parametrize("task_id,expected", [
    (21, 2),   # 逾期：done 11-07 − orig 11-05；以 latest_due（11-10）算會是 0、以今天算會是 6
    (22, 0),   # 提前完成
    (23, 0),   # 當天完成
    (26, 0),   # 完成日早於開始日（spec 6.5）
])
def test_f2_f3_overdue_days_is_server_computed_from_orig_due(client, seed, query, task_id, expected):
    seed(SEED)
    r = put(client, task_id, body(query, overdue_days=99))
    assert r.status_code == 201, r.text
    assert r.json()["feedback"]["overdue_days"] == expected
    assert query("SELECT overdue_days FROM completion_feedback")[0]["overdue_days"] == expected


def test_f4_writes_one_feedback_event_in_same_transaction(client, seed, query):
    seed(SEED)
    before = count(query, "events")
    out = put(client, 21, body(query, invest_vs_expected=None)).json()
    assert count(query, "events") == before + 1                     # 只多一筆：沒有 status、goal、due 事件
    ev = query("SELECT * FROM events")[0]
    assert ev["id"] == out["event"]["id"]
    assert (ev["kind"], ev["field"], ev["from_value"], ev["to_value"], ev["origin"]) == \
        ("feedback", "completion_feedback", None, str(out["feedback"]["id"]), "manual")
    assert (ev["task_id"], ev["task_title"], ev["project_id"], ev["mine"]) == (21, "畫面規格", 1, True)
    assert ev["extra"] == {"actual_stars": 4, "energy": "mid", "invest_vs_expected": None, "overdue_days": 2,
                           "rubric_id": rubric_id(query)}
    assert ev["ts"].isoformat() == NOW


def test_f4_event_mine_is_false_for_someone_elses_task(client, seed, query):
    seed(SEED)
    put(client, 22, body(query))
    assert query("SELECT mine FROM events WHERE kind = 'feedback'") == [{"mine": False}]


# ---------- F5～F7：必填、值域、量表版本 ----------

@pytest.mark.parametrize("field", ["actual_stars", "energy", "rubric_id"])
@pytest.mark.parametrize("how", ["omit", "null"])
def test_f5_required_fields(client, seed, query, field, how):
    seed(SEED)
    payload = body(query)
    if how == "omit":
        del payload[field]
    else:
        payload[field] = None
    assert_validation(put(client, 21, payload), [field])
    assert count(query, "completion_feedback") == 0 and count(query, "events") == 0
    assert task_row(query, 21)["status"] == "done"                  # 不可儲存，但可稍後補（6.5）
    assert 21 in [i["task_id"] for i in pending(client)["items"]]


@pytest.mark.parametrize("field,value", [
    ("actual_stars", 0), ("actual_stars", 6), ("actual_stars", 4.5), ("actual_stars", True), ("actual_stars", "4"),
    ("energy", "HIGH"), ("energy", ""), ("energy", "medium"),
    ("invest_vs_expected", ""), ("invest_vs_expected", "much"),
    ("rubric_id", True), ("rubric_id", "1"),
])
def test_f6_value_ranges(client, seed, query, field, value):
    seed(SEED)
    assert_validation(put(client, 21, body(query, **{field: value})), [field])
    assert count(query, "completion_feedback") == 0


@pytest.mark.parametrize("how", ["omit", "null"])
def test_f6_invest_vs_expected_is_optional(client, seed, query, how):
    seed(SEED)
    payload = body(query)
    if how == "omit":
        del payload["invest_vs_expected"]
    else:
        payload["invest_vs_expected"] = None
    r = put(client, 21, payload)
    assert r.status_code == 201, r.text
    assert r.json()["feedback"]["invest_vs_expected"] is None


def test_f6_error_response_does_not_echo_input(client, seed, query, caplog):
    seed(SEED)
    r = put(client, 21, body(query, energy=MARK54))
    assert r.status_code == 422
    assert MARK54 not in r.text and MARK54 not in caplog.text       # 資安規則 3


def test_f7_unknown_rubric_is_rejected(client, seed, query):
    seed(SEED)
    assert_validation(put(client, 21, body(query, rubric_id=99999)), ["rubric_id"])


def test_f7_older_rubric_is_kept_and_later_versions_do_not_change_it(client, seed, query):
    seed(SEED)
    old = rubric_id(query)
    seed(f"""INSERT INTO rubrics (id, version, levels, source, created_at) VALUES
      (50, 50, '["一","二","三","四","五"]', 'interview', {TS});""")
    r = put(client, 21, body(query, rubric_id=old))                 # 開面板時的版本（6.5）
    assert r.status_code == 201 and r.json()["feedback"]["rubric_id"] == old
    seed(f"""INSERT INTO rubrics (id, version, levels, source, created_at) VALUES
      (51, 51, '["1","2","3","4","5"]', 'interview', {TS});""")     # 之後換版（AC-45）
    assert client.get(f"{API}/tasks/21/feedback").json()["rubric_id"] == old
    assert query("SELECT rubric_id FROM completion_feedback")[0]["rubric_id"] == old
    assert query("SELECT extra FROM events WHERE kind = 'feedback'")[0]["extra"]["rubric_id"] == old


# ---------- F8～F10：任務狀態、重複、忽略的欄位 ----------

@pytest.mark.parametrize("task_id", [27, 28])
def test_f8_task_must_be_done(client, seed, query, task_id):
    seed(SEED)
    assert_validation(put(client, task_id, body(query)), ["task_id"])
    assert count(query, "completion_feedback") == 0 and count(query, "events") == 0


def test_f8_unknown_task_is_not_found(client, seed, query):
    seed(SEED)
    r = put(client, 9999, body(query))
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


def test_f9_second_feedback_is_rejected_and_first_is_unchanged(client, seed, query):
    seed(SEED)
    first = put(client, 21, body(query, actual_stars=4)).json()["feedback"]
    r = put(client, 21, body(query, actual_stars=1, energy="low"))
    assert r.status_code == 409 and r.json()["error"]["code"] == "FEEDBACK_EXISTS"
    assert client.get(f"{API}/tasks/21/feedback").json() == first
    assert count(query, "completion_feedback") == 1 and count(query, "events") == 1


def test_f10_client_values_for_server_fields_and_goal_are_ignored(client, seed, query):
    seed(SEED)
    before = task_row(query, 21)
    r = put(client, 21, body(query, overdue_days=99, task_id=999, id=777, created_at="2020-01-01T00:00:00+08:00",
                             mine=False, star_source="ai_accepted", goal_id=1))
    assert r.status_code == 201, r.text
    fb = r.json()["feedback"]
    assert (fb["task_id"], fb["overdue_days"], fb["created_at"]) == (21, 2, NOW)
    assert fb["id"] != 777
    assert r.json()["event"]["mine"] is True
    assert task_row(query, 21) == before                            # 任務整列不變（含 goal_id、star_source、version）
    assert query("SELECT count(*) AS n FROM events WHERE kind = 'goal'")[0]["n"] == 0


def test_f10_nonexistent_goal_id_is_not_even_read(client, seed, query):
    seed(SEED)
    assert put(client, 21, body(query, goal_id=99999)).status_code == 201


# ---------- F11：原子性（黑箱：以觸發器注入失敗，兩個方向） ----------

FAIL_ON_FEEDBACK_EVENT = """
CREATE FUNCTION qc_fail_fb_event() RETURNS trigger AS $$ BEGIN
  IF NEW.kind = 'feedback' THEN RAISE EXCEPTION 'qc injected'; END IF; RETURN NEW; END $$ LANGUAGE plpgsql;
CREATE TRIGGER qc_fail_fb_event BEFORE INSERT ON events FOR EACH ROW EXECUTE FUNCTION qc_fail_fb_event();
"""
FAIL_ON_FEEDBACK_ROW = """
CREATE FUNCTION qc_fail_fb_row() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'qc injected'; END $$ LANGUAGE plpgsql;
CREATE TRIGGER qc_fail_fb_row BEFORE INSERT ON completion_feedback FOR EACH ROW EXECUTE FUNCTION qc_fail_fb_row();
"""


@pytest.mark.parametrize("trigger", [FAIL_ON_FEEDBACK_EVENT, FAIL_ON_FEEDBACK_ROW], ids=["event-fails", "row-fails"])
def test_f11_failure_leaves_neither_feedback_nor_event(app, seed, query, trigger):
    seed(SEED + trigger)
    before = task_row(query, 21)
    with TestClient(app, raise_server_exceptions=False, headers={"Authorization": "Bearer test-token"}) as c:
        r = put(c, 21, body(query))
        assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"   # 注入確實觸發
        assert 21 in [i["task_id"] for i in pending(c)["items"]]
    assert count(query, "completion_feedback") == 0 and count(query, "events") == 0
    assert task_row(query, 21) == before


# ---------- F12：讀取回報 ----------

def test_f12_get_feedback(client, seed, query):
    seed(SEED)
    assert client.get(f"{API}/tasks/21/feedback").status_code == 404     # 還沒填
    saved = put(client, 21, body(query)).json()["feedback"]
    r = client.get(f"{API}/tasks/21/feedback")
    assert r.status_code == 200 and r.json() == saved
    missing = client.get(f"{API}/tasks/9999/feedback")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "NOT_FOUND"


# ---------- P1～P4：待補清單 ----------

def test_p1_p2_pending_lists_done_tasks_without_feedback_in_order(client, seed):
    seed(SEED)
    out = pending(client)
    ids = [i["task_id"] for i in out["items"]]
    # 依 done_date、task_id 由舊到新；不篩選：他人負責（22）、單點（23）、私人（24）、封存專案（25）都列
    assert ids == [29, 23, 26, 22, 25, 21, 24]
    assert out["total"] == 7
    assert len(out["items"]) >= 1
    for item in out["items"]:
        assert set(item) == PENDING_KEYS


def test_p2_p3_pending_item_values(client, seed):
    seed(SEED)
    by_id = {i["task_id"]: i for i in pending(client)["items"]}
    assert by_id[21] == {"task_id": 21, "title": "畫面規格", "owner": "我", "project_id": 1, "done_date": "2026-11-07",
                         "orig_due": "2026-11-05", "overdue_days": 2, "expected_stars": 3, "star_source": "self"}
    assert by_id[26]["overdue_days"] == 0 and by_id[22]["overdue_days"] == 0
    assert (by_id[29]["expected_stars"], by_id[29]["star_source"]) == (4, "ai_accepted")
    assert by_id[23]["project_id"] is None and by_id[22]["owner"] == "阿德"


def test_p4_filled_task_leaves_pending(client, seed, query):
    seed(SEED)
    put(client, 21, body(query))
    ids = [i["task_id"] for i in pending(client)["items"]]
    assert 21 not in ids and len(ids) == 6


def test_p1_empty_pending(client, seed, query):
    seed(f"""INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
      (1, 'p', 'work', 'manager', {TS}, {TS});
      INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, status,
        created_at, updated_at) VALUES (1, 1, 't', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-20', 'todo',
        {TS}, {TS});""")
    assert pending(client) == {"items": [], "total": 0}


# ---------- T1：伺服器今天 ----------

def test_t1_meta_today(client):
    r = client.get(f"{API}/meta/today")
    assert r.status_code == 200 and r.json() == {"today": "2026-11-11"}


def test_t1_meta_today_uses_taipei_date(client):
    # 台北 11-12 00:30 時 UTC 仍是 11-11：以 UTC 取日期的錯誤實作會回 11-11
    set_clock(FixedClock(datetime(2026, 11, 12, 0, 30, tzinfo=timezone(timedelta(hours=8)))))
    assert client.get(f"{API}/meta/today").json() == {"today": "2026-11-12"}


# ---------- A1、A2：9.4 精力與星數只由使用者填（FR-AI-06 防回歸，QC 持有） ----------

DONE_CANDIDATES = """
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
 (1, 'paste', '我', '10:00', '測試環境完成了', 'fb-h1', '2026-11-11T09:00+08:00', '2026-12-11T09:00+08:00'),
 (2, 'paste', '我', '10:05', '整合測試應該好了吧', 'fb-h2', '2026-11-11T09:00+08:00', '2026-12-11T09:00+08:00');
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, suggest, state, created_at) VALUES
 (1, 1, 'done', 'sure', 27, NULL, NULL, 'open', '2026-11-11T09:00+08:00'),
 (2, 2, 'unclear', 'to_clarify', 28, NULL, '{"kind":"done"}', 'open', '2026-11-11T09:00+08:00');
"""


def assert_no_feedback_created(client, query, task_id):
    assert task_row(query, task_id)["status"] == "done"             # 完成那一步確實成功（防空轉）
    assert count(query, "completion_feedback") == 0
    assert task_id in [i["task_id"] for i in pending(client)["items"]]


def test_a1_fr_ai06_complete_creates_no_feedback(client, seed, query):
    seed(SEED)
    r = client.post(f"{API}/tasks/27/complete", json={"expected_version": 1})
    assert r.status_code == 200 and r.json()["feedback_required"] is True
    assert_no_feedback_created(client, query, 27)


def test_a1_fr_ai06_confirm_done_candidate_creates_no_feedback(client, seed, query):
    seed(SEED + DONE_CANDIDATES)
    r = client.post(f"{API}/candidates/1/confirm", json={"expected_version": 1})
    assert r.status_code == 200, r.text
    assert r.json()["feedback_required"] is True
    assert_no_feedback_created(client, query, 27)


def test_a1_fr_ai06_clarify_done_candidate_creates_no_feedback(client, seed, query):
    seed(SEED + DONE_CANDIDATES)
    r = client.post(f"{API}/candidates/2/clarify", json={"expected_version": 1})
    assert r.status_code == 200, r.text
    assert_no_feedback_created(client, query, 28)


def test_a1_fr_ai06_ai_supplied_energy_and_stars_are_never_used(client, seed, query, ai):
    seed(SEED)
    ai.script("AI-01", {"items": [{"ref": 1, "kind": "done", "task_id": 27, "certainty": "sure",
                                   "energy": "high", "actual_stars": 5, "note": "AIGUESS 很輕鬆"}]})
    r = ingest(client, "[10:00] 我：測試環境完成了")
    assert r.status_code == 200, r.text
    cand = r.json()["candidates"][0]
    assert "AIGUESS" not in r.text
    c = client.post(f"{API}/candidates/{cand['id']}/confirm", json={"expected_version": cand["task"]["version"]})
    assert c.status_code == 200, c.text
    assert_no_feedback_created(client, query, 27)
    payload = body(query)
    del payload["actual_stars"]
    assert_validation(put(client, 27, payload), ["actual_stars"])  # AI 夾帶的值沒有被當成預設
    assert "AIGUESS" not in client.get(f"{API}/feedback/pending").text


def test_a1_fr_ai06_saved_values_come_only_from_the_user(client, seed, query):
    seed(SEED)
    r = put(client, 29, body(query, actual_stars=2, energy="low"))  # 任務事前預設 4 星、來源 ai_accepted
    assert r.status_code == 201
    assert query("SELECT actual_stars, energy FROM completion_feedback") == [{"actual_stars": 2, "energy": "low"}]


def test_a2_fr_ai06_feedback_flow_never_calls_ai(client, seed, query, ai):
    seed(SEED)
    runs = count(query, "ai_runs")
    for task_id in (21, 24):                                        # 工作與私人
        pending(client)
        assert put(client, task_id, body(query)).status_code == 201
        assert client.get(f"{API}/tasks/{task_id}/feedback").status_code == 200
    client.get(f"{API}/meta/today")
    assert ai.calls == [] and count(query, "ai_runs") == runs


# ---------- 其他：冪等、認證、週報不外洩回報 ----------

def test_i1_idempotent_replay_returns_same_response(client, seed, query):
    seed(SEED)
    h = {"Idempotency-Key": "fb-1"}
    first = put(client, 21, body(query), headers=h)
    again = put(client, 21, body(query), headers=h)
    assert first.status_code == again.status_code == 201
    assert again.headers.get("Idempotent-Replay") == "true"
    assert again.json() == first.json()
    assert count(query, "completion_feedback") == 1


@pytest.mark.parametrize("method,path", [
    ("GET", "/feedback/pending"), ("PUT", "/tasks/21/feedback"), ("GET", "/tasks/21/feedback"), ("GET", "/meta/today"),
])
def test_new_endpoints_require_token(app, seed, query, method, path):
    seed(SEED)
    with TestClient(app) as anon:
        r = anon.request(method, f"{API}{path}", json=body(query) if method == "PUT" else None)
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"
    assert "畫面規格" not in r.text and "訂機票" not in r.text
    assert count(query, "completion_feedback") == 0


def test_weekly_ai05_payload_never_includes_feedback(client, seed, query, ai):
    """spec 5.3a：AI-05 不送完成回報的星數與精力；完成項目的 event_id 仍是 status 事件。"""
    seed(SEED)
    done = client.post(f"{API}/tasks/27/complete", json={"expected_version": 1, "done_date": "2026-11-10"})
    assert done.status_code == 200
    status_event = done.json()["event"]["id"]
    fb_event = put(client, 27, body(query, energy="high", actual_stars=5)).json()["event"]["id"]
    assert client.post(f"{API}/reports/weekly/draft", json={"week_start": "2026-11-09"}).status_code == 200
    payloads = [p for n, p in ai.calls if n == "AI-05"]
    assert payloads, "沒有呼叫 AI-05，斷言會空轉"
    sent = payloads[0]
    assert [d["event_id"] for d in sent["done"] if d["task_id"] == 27] == [status_event]
    text = str(sent)
    assert str(fb_event) not in [str(d.get("event_id")) for d in sent["done"]]
    assert "energy" not in text and "actual_stars" not in text and "high" not in text
