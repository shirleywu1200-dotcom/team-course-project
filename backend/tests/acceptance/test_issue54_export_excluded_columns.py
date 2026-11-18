"""#54：匯出排除夾帶敏感內容的欄位（spec 6.7、AC-54；2026-11-17 產品負責人裁定，併 #46）。

Dev-A 依 DA-27 暫代撰寫；只經 HTTP 與 SQL 種子操作，排除清單照 spec 6.7 寫死在測試裡，不讀實作。
欄位集合以資料庫的 information_schema 為基準。每個被排除的欄位放一個專屬 ASCII 標記（不和 helpers.MARK 共用，
也不用人名），對整份匯出本文做全文檢查；照帶欄位放另一組標記，證明全文檢查本身有效。
允許清單是結構斷言：要逼「之後新增或改名欄位時當下決定能不能匯出」，行為測試做不到（資安規則 5、#54 作法 2）。
"""

import pytest

from tests.acceptance.helpers import API, SEED_BASE

TS = "'2026-11-11T09:00+08:00'"
RCV = "'2026-11-11T09:00+08:00', '2026-12-11T09:00+08:00'"

# 被排除欄位的標記（spec 6.7）；任何一個出現在匯出本文就是外流
LEAK_MARKS = {"TOK54", "RESP54", "DRAFT54", "SPK54", "HASH54", "RAW54"}
# 照帶欄位的標記：必須出現，證明全文檢查有看到內容
KEPT_MARKS = {"MANUAL54", "EXCERPT54"}

SEED54 = SEED_BASE + f"""
INSERT INTO line_groups (id, name, kind, line_ref, notified, bound) VALUES (1, '客戶群組', 'client', 'ref-1', true, true);
INSERT INTO goals (id, type, title, period, target, energy_plan, created_at) VALUES
 (1, 'growth', '學會 SQL 視窗函式', '2026Q4', 3, 'mid', {TS});
INSERT INTO completion_feedback (id, task_id, actual_stars, energy, invest_vs_expected, overdue_days, rubric_id, created_at)
 VALUES (1, 7, 4, 'mid', 'as_expected', 0, 1, {TS});
INSERT INTO sources (id, channel, line_group_id, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at,
                     purged_at) VALUES
 (1, 'paste', NULL, 'SPK54-A', '10:12', '畫面規格延到 11/18 EXCERPT54', 'HASH54-A', {RCV}, NULL),
 (2, 'line', 1, 'SPK54-B', '10:15', NULL, 'HASH54-B', {RCV}, '2026-11-11T09:30+08:00');
INSERT INTO jobs (id, kind, status, attempts, payload, result, error, created_at, updated_at) VALUES
 (1, 'ingest', 'succeeded', 1, '{{"source_ids": [1, 2], "project_id": 1, "duplicates": 0, "unparsed_lines": [3]}}',
  '{{"created": 1, "skipped": 1, "duplicates": 0, "unparsed_lines": [3]}}', NULL, {TS}, {TS});
INSERT INTO ai_runs (id, node_id, job_id, status, attempt, latency_ms, raw_output, error, created_at) VALUES
 (1, 'AI-01', 1, 'ok', 1, 120, '{{"items": [], "echo": "RAW54"}}', NULL, {TS}),
 (2, 'AI-05', NULL, 'ok', 1, 30, NULL, NULL, {TS});
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, state, ai_run_id, created_at) VALUES
 (1, 1, 'delay', 'sure', 1, '{{"new_due": "2026-11-18"}}', 'open', 1, {TS});
INSERT INTO batches (id, project_id, days, task_count, created_at) VALUES (1, 1, 3, 2, {TS});
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, delta_days, mine)
 VALUES (1, '2026-11-05T12:00+08:00', 1, 1, '畫面規格 v1', 'due', 'latest_due', '2026-11-12', '2026-11-13', 'manual', 1,
         false);
INSERT INTO ai_feedback (id, node_id, target_type, target_id, outcome, detail, created_at) VALUES
 (1, 'AI-07', 'import_map', 1, 'changed',
  '{{"ai_run_id": 1, "ai": {{"title": 0, "owner": 1, "start": 2, "end": 3}},
    "final": {{"title": 0, "owner": 2, "start": 2, "end": 3}}}}', {TS}),
 (2, 'AI-01', 'candidate', 1, 'changed', '{{"task_id": 9}}', {TS}),
 (3, 'AI-06', 'rubric', 1, 'accepted', NULL, {TS});
INSERT INTO reports (id, kind, period_start, goal_id, ai_draft, manual_text, excluded_private, created_at, updated_at,
                     ai_items, ai_status) VALUES
 (1, 'weekly', '2026-11-02', NULL, '【本週完成】DRAFT54-A', '給主管的人工版 MANUAL54', 1, {TS}, {TS},
  '[{{"section": "done", "task_id": 7, "event_id": 1}}]', 'ok'),
 (2, 'weekly', '2026-11-09', NULL, '', '', 0, {TS}, {TS}, NULL, 'unavailable'),
 (3, 'goal', NULL, 1, NULL, NULL, 0, {TS}, {TS}, NULL, NULL);
INSERT INTO confirmations (token, task_id, payload, task_version, expires_at, used_at) VALUES
 ('TOK54-A', 1, '{{"new_orig_due": "2026-11-20", "type": "plan_error", "reason": "需求變更", "orig_due": "2026-11-13"}}',
  1, '2026-11-11T09:10+08:00', NULL),
 ('TOK54-B', 2, '{{"new_orig_due": "2026-11-21", "type": "plan_error", "reason": "估錯", "orig_due": "2026-11-14"}}',
  1, '2026-11-10T09:10+08:00', '2026-11-10T09:05+08:00');
INSERT INTO idempotency_keys (key, endpoint, response, created_at) VALUES
 ('k1', 'POST /api/v1/tasks/1/baseline/preview',
  '{{"status": 200, "body": {{"confirmation_token": "TOK54-A", "impact": {{"note": "RESP54-1"}}}}}}', {TS}),
 ('k2', 'POST /api/v1/inbox/ingest',
  '{{"status": 200, "body": {{"result": {{"candidates": [{{"speaker": "RESP54-SPK", "quote": "RESP54-Q"}}]}}}}}}', {TS}),
 ('k3', 'PATCH /api/v1/tasks/1', '{{"status": 409, "body": {{"error": {{"code": "STALE_VERSION", "message": "RESP54-ERR"}}}}}}',
  {TS});
"""

# spec 6.7 的排除欄位（#40、#54）
EXCLUDED = {
    "ai_runs": {"raw_output"},
    "confirmations": {"token"},
    "idempotency_keys": {"response"},
    "reports": {"ai_draft"},
    "sources": {"speaker", "excerpt_hash"},
}

# 允許清單：這些表之後新增或改名欄位時測試失敗，逼當下決定該欄能不能匯出（#54 作法 2）
ALLOWED = {
    "ai_runs": {"id", "node_id", "job_id", "status", "attempt", "latency_ms", "error", "created_at"},
    "confirmations": {"task_id", "payload", "task_version", "expires_at", "used_at"},
    "idempotency_keys": {"key", "endpoint", "created_at"},
    "reports": {"id", "kind", "period_start", "goal_id", "manual_text", "excluded_private", "created_at",
                "updated_at", "ai_items", "ai_status"},
    "sources": {"id", "channel", "line_group_id", "spoken_at", "excerpt", "received_at", "expires_at", "purged_at"},
    "jobs": {"id", "kind", "status", "attempts", "payload", "result", "error", "created_at", "updated_at"},
    "ai_feedback": {"id", "node_id", "target_type", "target_id", "outcome", "detail", "created_at"},
}

# 匯出的表：新增一張表時這裡會失敗，逼當下決定新表的欄位能不能匯出（資安規則 5）
ALL_TABLES = {"ai_feedback", "ai_runs", "batches", "candidates", "completion_feedback", "confirmations", "events",
              "goals", "idempotency_keys", "jobs", "line_groups", "projects", "reports", "rubrics", "settings",
              "sources", "tasks"}


def columns(query, table):
    rows = query("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema = 'public' AND table_name = :t", t=table)
    return {r["column_name"] for r in rows}


def count(query, table):
    return query(f'SELECT count(*) AS n FROM "{table}"')[0]["n"]  # noqa: S608 表名為測試內的常數


@pytest.fixture
def exported(client, seed):
    seed(SEED54)
    r = client.post(f"{API}/export")
    assert r.status_code == 200, r.text
    return r


def rows_of(exported, table):
    return exported.json()["tables"][table]


def assert_no_keys(rows, keys):
    assert rows, "表沒有資料，斷言會空轉"
    for row in rows:
        assert not (keys & set(row)), row


# ---------- E1～E4：被排除的欄位不帶鍵，其餘照帶，筆數一致 ----------

def test_e1_confirmations_have_no_token(exported, query):
    rows = rows_of(exported, "confirmations")
    assert_no_keys(rows, {"token"})
    assert exported.json()["counts"]["confirmations"] == len(rows) == count(query, "confirmations") == 2
    # token 是主鍵，拿掉後以其餘欄位整體比對
    got = sorted((r["task_id"], r["task_version"], r["payload"]["reason"], r["expires_at"][:16], r["used_at"])
                 for r in rows)
    assert got == [(1, 1, "需求變更", "2026-11-11T09:10", None),
                   (2, 1, "估錯", "2026-11-10T09:10", "2026-11-10T09:05:00+08:00")]


def test_e2_idempotency_keys_have_no_response(exported, query):
    rows = rows_of(exported, "idempotency_keys")
    assert_no_keys(rows, {"response"})
    assert exported.json()["counts"]["idempotency_keys"] == len(rows) == count(query, "idempotency_keys") == 3
    assert sorted((r["key"], r["endpoint"]) for r in rows) == [
        ("k1", "POST /api/v1/tasks/1/baseline/preview"), ("k2", "POST /api/v1/inbox/ingest"),
        ("k3", "PATCH /api/v1/tasks/1")]


def test_e3_reports_have_no_ai_draft_and_keep_manual_text(exported, query):
    rows = rows_of(exported, "reports")
    assert_no_keys(rows, {"ai_draft"})                  # 有值、空字串、NULL 都不帶鍵
    assert exported.json()["counts"]["reports"] == len(rows) == count(query, "reports") == 3
    by_id = {r["id"]: r for r in rows}
    assert [by_id[i]["manual_text"] for i in (1, 2, 3)] == ["給主管的人工版 MANUAL54", "", None]
    assert (by_id[1]["ai_status"], by_id[1]["excluded_private"], by_id[1]["ai_items"]) == \
        ("ok", 1, [{"section": "done", "task_id": 7, "event_id": 1}])
    assert (by_id[3]["kind"], by_id[3]["goal_id"], by_id[3]["period_start"]) == ("goal", 1, None)


def test_e4_sources_have_no_speaker_or_hash_and_keep_excerpt(exported, query):
    rows = rows_of(exported, "sources")
    assert_no_keys(rows, {"speaker", "excerpt_hash"})   # 未清除與已清除都不帶
    assert exported.json()["counts"]["sources"] == len(rows) == count(query, "sources") == 2
    by_id = {r["id"]: r for r in rows}
    assert by_id[1]["excerpt"] == "畫面規格延到 11/18 EXCERPT54"   # 未清除的原文照匯出（spec 6.7）
    assert by_id[2]["excerpt"] is None and by_id[2]["purged_at"] is not None
    assert (by_id[2]["channel"], by_id[2]["line_group_id"], by_id[2]["spoken_at"]) == ("line", 1, "10:15")


# ---------- E5：核對後為純結構化的欄位照帶 ----------

def test_e5_feedback_detail_and_job_payload_are_kept(exported):
    detail = {r["id"]: r["detail"] for r in rows_of(exported, "ai_feedback")}
    assert detail[1]["final"] == {"title": 0, "owner": 2, "start": 2, "end": 3}
    assert detail[2] == {"task_id": 9} and detail[3] is None
    job = rows_of(exported, "jobs")[0]
    assert job["payload"] == {"source_ids": [1, 2], "project_id": 1, "duplicates": 0, "unparsed_lines": [3]}
    assert job["result"]["unparsed_lines"] == [3]


# ---------- E6：允許清單鎖定 ----------

def test_e6_locked_tables_export_exactly_the_allowed_columns(exported, query):
    tables = exported.json()["tables"]
    for table, allowed in ALLOWED.items():
        db_cols = columns(query, table)
        assert EXCLUDED.get(table, set()) <= db_cols, table   # 資料庫仍有這些欄，只是不匯出
        assert db_cols - EXCLUDED.get(table, set()) == allowed, table
        assert tables[table], f"{table} 沒有資料，斷言會空轉"
        for row in tables[table]:
            assert set(row) == allowed, table


def test_e6_exported_table_set_is_locked(exported):
    body = exported.json()
    assert set(body["tables"]) == set(body["counts"]) == ALL_TABLES


# ---------- E7：其他表照帶全部欄位 ----------

def test_e7_other_tables_keep_all_columns(exported, query):
    tables = exported.json()["tables"]
    others = ALL_TABLES - set(ALLOWED)
    assert others == {"batches", "candidates", "completion_feedback", "events", "goals", "line_groups", "projects",
                      "rubrics", "settings", "tasks"}
    for table in others:
        assert tables[table], f"{table} 沒有資料，斷言會空轉"
        for row in tables[table]:
            assert set(row) == columns(query, table), table


# ---------- E8：全文檢查 ----------

def test_e8_no_excluded_content_anywhere_in_export(exported):
    text = exported.text
    assert {m for m in LEAK_MARKS if m in text} == set()
    assert {m for m in KEPT_MARKS if m in text} == KEPT_MARKS


# ---------- E9：匯出不改資料庫 ----------

SENSITIVE = {
    "confirmations": "SELECT token FROM confirmations ORDER BY token",
    "idempotency_keys": "SELECT key, response FROM idempotency_keys ORDER BY key",
    "reports": "SELECT id, ai_draft, manual_text FROM reports ORDER BY id",
    "sources": "SELECT id, speaker, excerpt_hash FROM sources ORDER BY id",
    "ai_runs": "SELECT id, raw_output FROM ai_runs ORDER BY id",
}


def test_e9_export_does_not_touch_stored_values(client, seed, query):
    seed(SEED54)
    before = {t: query(sql) for t, sql in SENSITIVE.items()}
    assert client.post(f"{API}/export").status_code == 200
    assert {t: query(sql) for t, sql in SENSITIVE.items()} == before


# ---------- E10：空表 ----------

def test_e10_empty_tables_export_as_empty_lists(client, seed):
    seed(SEED_BASE)
    body = client.post(f"{API}/export").json()
    for table in ("confirmations", "idempotency_keys", "reports", "sources"):
        assert table in body["tables"], table
        assert body["tables"][table] == [] and body["counts"][table] == 0, table
