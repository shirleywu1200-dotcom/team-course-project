"""#40：匯出不帶 ai_runs.raw_output（spec 6.7、AC-54；2026-11-17 產品負責人裁定）。

Dev-A 依 DA-27 暫代撰寫；只經 HTTP 與 SQL 種子操作。欄位集合以資料庫的 information_schema 為基準，
未來遷移新增欄位時測試不必跟著改。標記只放在 raw_output，全文檢查才不會被其他欄位誤判。
"""

from tests.acceptance.helpers import API, MARK, SEED_BASE

TS = "'2026-11-11T09:00+08:00'"
RUNS = f"""
INSERT INTO ai_runs (id, node_id, status, attempt, latency_ms, raw_output, error, created_at) VALUES
 (1, 'AI-01', 'ok',             1, 120, '{{"items": [], "echo": "{MARK}有值"}}', NULL,              {TS}),
 (2, 'AI-01', 'invalid_output', 2,  80, '{MARK} 原句回聲',                        'AIInvalidOutput', {TS}),
 (3, 'AI-06', 'ok',             1,  50, '',                                       NULL,              {TS}),
 (4, 'AI-07', 'error',          1,  10, NULL,                                     'AITimeout',       {TS}),
 (5, 'AI-05', 'ok',             1,  30, NULL,                                     NULL,              {TS});
"""


def columns(query, table):
    rows = query("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema = 'public' AND table_name = :t", t=table)
    return {r["column_name"] for r in rows}


def export(client):
    r = client.post(f"{API}/export")
    assert r.status_code == 200, r.text
    return r


def test_ai_runs_rows_have_no_raw_output_and_keep_other_columns(client, seed, query):
    seed(SEED_BASE + RUNS)
    r = export(client)
    runs = r.json()["tables"]["ai_runs"]
    assert len(runs) == 5 and r.json()["counts"]["ai_runs"] == 5
    expected = columns(query, "ai_runs") - {"raw_output"}
    assert "raw_output" in columns(query, "ai_runs")   # 資料庫仍有這欄，只是不匯出
    # 允許清單：ai_runs 之後新增或改名欄位時這裡會失敗，逼當下決定該欄能不能匯出（資安規則 5；code-review）
    assert expected == {"id", "node_id", "job_id", "status", "attempt", "latency_ms", "error", "created_at"}
    for row in runs:
        assert set(row) == expected                     # 有值、空字串、NULL、從未寫入都不帶鍵
    by_id = {row["id"]: row for row in runs}
    assert (by_id[2]["node_id"], by_id[2]["status"], by_id[2]["attempt"], by_id[2]["error"]) == \
        ("AI-01", "invalid_output", 2, "AIInvalidOutput")
    assert by_id[4]["latency_ms"] == 10 and by_id[1]["created_at"].startswith("2026-11-11")
    assert MARK not in r.text


def test_other_tables_keep_all_columns(client, seed, query):
    seed(SEED_BASE + RUNS)
    tables = export(client).json()["tables"]
    for table, rows in tables.items():
        if table == "ai_runs" or not rows:
            continue
        assert set(rows[0]) == columns(query, table), table


def test_empty_ai_runs_exports_empty_list(client, seed):
    seed(SEED_BASE)
    body = export(client).json()
    assert body["tables"]["ai_runs"] == [] and body["counts"]["ai_runs"] == 0


def test_export_does_not_touch_stored_raw_output(client, seed, query):
    seed(SEED_BASE + RUNS)
    before = query("SELECT id, raw_output FROM ai_runs ORDER BY id")
    export(client)
    assert query("SELECT id, raw_output FROM ai_runs ORDER BY id") == before
