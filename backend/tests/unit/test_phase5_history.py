"""Phase 5：歷程查詢與甘特資料（AC-27、28、34、56，todo 5.1–5.6）。"""

import time

from tests.unit.seeds import BASE

EVENTS = "/api/v1/events"

# 來源 1 原文仍在；來源 2 已依保存期限清除（AC-28）
HISTORY = """
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at, purged_at) VALUES
  (1, 'paste', '阿德', '10:12', '畫面規格 v1 確定延到 11/18', 'h1',
      '2026-11-10T10:12+08:00', '2026-12-10T10:12+08:00', NULL),
  (2, 'paste', '小薇', '09:00', NULL, 'h2',
      '2026-10-01T09:00+08:00', '2026-10-31T09:00+08:00', '2026-11-01T03:00+08:00');

INSERT INTO batches (id, project_id, days, reason, task_count, created_at) VALUES
  (7, 1, 3, 'scope_change_external', 2, '2026-11-10T15:00+08:00');

INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value,
                    origin, origin_ref, source_id, reason, delta_days, mark, mine, ref_event_id, batch_id) VALUES
  (1, '2026-11-09T09:00+08:00', 1, 2, '畫面規格 v1', 'due', 'latest_due', '2026-11-13', '2026-11-18',
      'candidate', 12, 1, NULL, 5, NULL, false, NULL, NULL),
  (2, '2026-11-09T10:00+08:00', 1, 3, 'API 介面定義', 'status', 'status', 'todo', 'doing',
      'candidate', 13, 2, NULL, NULL, NULL, false, NULL, NULL),
  (3, '2026-11-10T15:00+08:00', 1, 4, '確認驗收條件', 'due', 'latest_due', '2026-11-18', '2026-11-21',
      'bulk', 7, NULL, 'scope_change_external', 3, NULL, true, NULL, 7),
  (4, '2026-11-10T15:00+08:00', 1, 5, '測試計畫', 'due', 'latest_due', '2026-11-20', '2026-11-23',
      'bulk', 7, NULL, 'scope_change_external', 3, NULL, true, NULL, 7),
  (5, '2026-11-10T16:00+08:00', 1, 4, '確認驗收條件', 'annotation', 'mark', NULL, 'worse',
      'manual', NULL, NULL, NULL, NULL, 'worse', true, 3, NULL),
  (6, '2026-11-11T09:00+08:00', NULL, 6, '繳交季報', 'due', 'latest_due', '2026-11-19', '2026-11-20',
      'manual', NULL, NULL, 'underestimated', 1, 'better', true, NULL, NULL),
  (7, '2026-11-11T09:30+08:00', 2, 7, '別專案任務', 'task', 'owner_name', '我', '阿德',
      'manual', NULL, NULL, NULL, NULL, NULL, true, NULL, NULL),
  (8, '2026-11-11T09:40+08:00', 1, NULL, '', 'project', 'name', '舊名', '會員系統 2.0 改版',
      'manual', NULL, NULL, NULL, NULL, NULL, false, NULL, NULL);
"""

OPEN_CANDIDATES = """
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, state, created_at) VALUES
  (12, 1, 'delay', 'sure', 2, '{"new_due":"2026-11-25"}', 'open', '2026-11-10T10:12+08:00'),
  (13, 1, 'stuck', 'sure', 3, NULL, 'open', '2026-11-10T10:12+08:00'),
  (14, 1, 'done',  'sure', 7, NULL, 'open', '2026-11-10T10:12+08:00'),
  (15, 1, 'unmatched', 'to_match', NULL, NULL, 'open', '2026-11-10T10:12+08:00'),
  (16, 1, 'delay', 'sure', 4, NULL, 'ignored', '2026-11-10T10:12+08:00');
"""


def ids(resp) -> list[int]:
    return [i["id"] for i in resp.json()["items"]]


# ---------- 5.1 篩選與分頁（AC-27） ----------

def test_ac27_filters_combine_and_total(client, seed):
    seed(BASE + HISTORY)
    r = client.get(EVENTS, params={"project_id": 1, "kind": "due"})
    assert r.status_code == 200
    assert ids(r) == [4, 3, 1] and r.json()["total"] == 3
    r = client.get(EVENTS, params={"project_id": 1, "kind": "due", "task_id": 4})
    assert ids(r) == [3] and r.json()["total"] == 1
    assert client.get(EVENTS, params={"batch_id": 7}).json()["total"] == 2


def test_ac27_project_none_returns_only_single_task_events(client, seed):
    seed(BASE + HISTORY)
    r = client.get(EVENTS, params={"project_id": "none"})
    assert ids(r) == [6] and r.json()["items"][0]["project_name"] is None


def test_date_range_is_inclusive_in_taipei(client, seed):
    seed(BASE + HISTORY)
    assert ids(client.get(EVENTS, params={"from": "2026-11-10", "to": "2026-11-10"})) == [5, 4, 3]


def test_pagination_total_and_stable_order_with_same_ts(client, seed):
    seed(BASE + HISTORY)
    page1 = client.get(EVENTS, params={"limit": 3, "offset": 0})
    page2 = client.get(EVENTS, params={"limit": 3, "offset": 3})
    page3 = client.get(EVENTS, params={"limit": 3, "offset": 6})
    assert page1.json()["total"] == 8
    assert ids(page1) + ids(page2) + ids(page3) == [8, 7, 6, 5, 4, 3, 2, 1]   # 事件 3、4 同 ts，以 id 排序


def test_invalid_params_are_validation_errors(client, seed):
    seed(BASE)
    for params in ({"limit": 501}, {"kind": "bogus"}, {"project_id": "abc"}, {"offset": -1}):
        r = client.get(EVENTS, params=params)
        assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR", params


def test_unknown_project_is_not_found(client, seed):
    seed(BASE)
    assert client.get(EVENTS, params={"project_id": 99}).json()["error"]["code"] == "NOT_FOUND"
    assert client.get("/api/v1/projects/99/history").status_code == 404
    assert client.get("/api/v1/projects/99/gantt").status_code == 404


def test_project_history_equals_events_with_project_filter(client, seed):
    seed(BASE + HISTORY)
    a = client.get("/api/v1/projects/1/history", params={"kind": "due"}).json()
    b = client.get(EVENTS, params={"project_id": 1, "kind": "due"}).json()
    assert a == b


# ---------- 5.2 有效註記、5.3 來源（AC-28） ----------

def test_effective_mark_only_on_due_events(client, seed):
    seed(BASE + HISTORY)
    by_id = {i["id"]: i for i in client.get(EVENTS).json()["items"]}
    assert by_id[3]["effective_mark"] == "worse"      # 有 annotation，取最新註記
    assert by_id[3]["mark"] is None                    # 原事件不變
    assert by_id[6]["effective_mark"] == "better"     # 沒有 annotation，取原事件
    assert by_id[1]["effective_mark"] is None
    assert by_id[5]["effective_mark"] is None and by_id[7]["effective_mark"] is None


def test_ac28_purged_source_keeps_event(client, seed):
    seed(BASE + HISTORY)
    by_id = {i["id"]: i for i in client.get(EVENTS).json()["items"]}
    assert by_id[1]["source"] == {"label": "候選 #12", "quote": "畫面規格 v1 確定延到 11/18", "purged": False}
    assert by_id[2]["source"] == {"label": "候選 #13", "quote": None, "purged": True}


def test_source_labels_by_origin(client, seed):
    seed(BASE + HISTORY)
    by_id = {i["id"]: i["source"] for i in client.get(EVENTS).json()["items"]}
    assert by_id[3] == {"label": "整批順延 #7", "quote": None, "purged": False}
    assert by_id[6]["label"] == "手動"
    assert by_id[8]["label"] == "手動" and by_id[8]["quote"] is None


def test_item_fields_match_spec_example(client, seed):
    seed(BASE + HISTORY)
    item = client.get(EVENTS, params={"task_id": 2}).json()["items"][0]
    assert item["project_name"] == "會員系統 2.0 改版" and item["ts"] == "2026-11-09T09:00:00+08:00"
    assert item["mine"] is False and item["delta_days"] == 5 and item["origin"] == "candidate"


# ---------- 5.4 甘特、5.5 摘要（AC-34） ----------

def test_gantt_rows_range_and_summary(client, seed):
    seed(BASE + HISTORY)
    body = client.get("/api/v1/projects/1/gantt").json()
    assert body["range"] == {"from": "2026-11-03", "to": "2026-11-20"}
    assert body["today"] == "2026-11-11"
    assert [r["task_id"] for r in body["rows"]] == [1, 2, 3, 4, 5]   # 含已完成任務，依開始日排序
    row3 = next(r for r in body["rows"] if r["task_id"] == 3)
    assert row3 == {"task_id": 3, "title": "API 介面定義", "owner": "小薇", "status": "doing",
                    "start": "2026-11-09", "orig_due": "2026-11-12", "latest_due": "2026-11-15",
                    "delta_days": 3, "done_date": None, "blocked": False, "version": 4}
    assert body["rows"][0]["done_date"] == "2026-11-10"
    assert body["summary"] == {"done": 1, "total": 5, "delayed": 1, "open_candidates": 0}


def test_gantt_negative_delta_for_early_task(client, seed):
    seed(BASE + "UPDATE tasks SET latest_due = '2026-11-16' WHERE id = 5;")
    row5 = next(r for r in client.get("/api/v1/projects/1/gantt").json()["rows"] if r["task_id"] == 5)
    assert row5["delta_days"] == -4 and row5["orig_due"] == "2026-11-20"


def test_gantt_empty_project(client, seed):
    seed(BASE + """INSERT INTO projects (id, name, scope, audience, created_at, updated_at)
                   VALUES (3, '空專案', 'work', 'none', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00');""")
    body = client.get("/api/v1/projects/3/gantt").json()
    assert body["range"] is None and body["rows"] == []
    assert body["summary"] == {"done": 0, "total": 0, "delayed": 0, "open_candidates": 0}


def test_ac34_open_candidates_do_not_affect_gantt(client, seed):
    seed(BASE + HISTORY)
    before = client.get("/api/v1/projects/1/gantt").json()
    seed(OPEN_CANDIDATES)
    after = client.get("/api/v1/projects/1/gantt").json()
    assert after["rows"] == before["rows"] and after["range"] == before["range"]
    assert after["summary"] == before["summary"] | {"open_candidates": 2}   # 12、13；14 屬專案 2，15 無任務，16 已忽略
    assert client.get(EVENTS).json()["total"] == 8                          # 候選不產生歷程


# ---------- 5.6 效能（AC-56，〔假設〕300 ms） ----------

def test_ac56_events_query_performance(client, seed):
    seed(BASE)
    seed("""
    INSERT INTO tasks (project_id, title, owner_name, scope, start_date, orig_due, latest_due,
                       created_at, updated_at)
    SELECT 1 + (g % 2), '任務 ' || g, CASE WHEN g % 3 = 0 THEN '我' ELSE '阿德' END, 'work',
           DATE '2026-11-01', DATE '2026-11-20', DATE '2026-11-20',
           '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00'
      FROM generate_series(1, 993) g;
    INSERT INTO events (ts, project_id, task_id, task_title, kind, field, from_value, to_value,
                        origin, delta_days, mark, mine)
    SELECT TIMESTAMPTZ '2026-11-01T09:00+08:00' + (g || ' minutes')::interval,
           1 + (g % 2), 8 + (g % 993), '任務', 'due', 'latest_due', '2026-11-20', '2026-11-21',
           'manual', 1, NULL, g % 3 = 0
      FROM generate_series(1, 10000) g;
    ANALYZE;
    """)
    queries = [{"project_id": 1}, {"project_id": 2, "kind": "due"}, {"task_id": 500}, {}]
    client.get(EVENTS, params={"project_id": 1})   # 暖機
    for params in queries:
        start = time.perf_counter()
        r = client.get(EVENTS, params=params)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert r.status_code == 200
        assert elapsed_ms < 300, (params, round(elapsed_ms))
