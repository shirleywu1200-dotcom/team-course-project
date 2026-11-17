"""AC-54：匯出為合法 JSON、含所有表、筆數與資料庫一致（FR-GOV-02、spec 6.7）。"""

import json

import pytest
from fastapi.testclient import TestClient

from tests.acceptance.helpers import API, MARK, SEED_BASE, SEED_CANDIDATES, count
from tests.conftest import TEST_TOKEN

# DDL（遷移 0001）中的業務表。idempotency_keys、confirmations 是暫存與憑證，是否匯出未裁定（規格歧義 14），另外驗。
BUSINESS_TABLES = ["settings", "rubrics", "line_groups", "projects", "goals", "tasks", "completion_feedback",
                   "sources", "jobs", "ai_runs", "candidates", "batches", "events", "ai_feedback", "reports"]

SEED_EXTRA = f"""
INSERT INTO ai_runs (id, node_id, status, attempt, raw_output, created_at) VALUES
 (1, 'AI-01', 'ok', 1, '{{"items": [], "echo": "{MARK}RAW"}}', '2026-11-11T09:00+08:00');
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, delta_days, mine) VALUES
 (1, '2026-11-05T12:00+08:00', 1, 1, '畫面規格 v1', 'due', 'latest_due', '2026-11-12', '2026-11-13', 'manual', 1, false);
"""


@pytest.fixture
def export(client, seed):
    seed(SEED_BASE + SEED_CANDIDATES + SEED_EXTRA)
    r = client.post(f"{API}/export")
    assert r.status_code == 200, r.text
    return r


def test_ac54_export_is_valid_json_with_all_business_tables(export):
    body = json.loads(export.content)
    assert set(BUSINESS_TABLES) <= set(body["tables"])


def test_ac54_row_counts_match_database(export, query):
    body = export.json()
    assert body["tables"]
    for table, rows in body["tables"].items():
        n = count(query, table)
        assert len(rows) == n, table
        assert body["counts"][table] == n, table
    assert len(body["tables"]["tasks"]) == 9 and len(body["tables"]["sources"]) == 8


def test_ac54_export_contains_actual_rows(export):
    tables = export.json()["tables"]
    assert {t["title"] for t in tables["tasks"]} >= {"畫面規格 v1", "API 介面定義"}
    assert tables["events"][0]["from_value"] == "2026-11-12"
    assert any(MARK in (s["excerpt"] or "") for s in tables["sources"])  # 未清除的原文照匯出


def test_ac54_purged_excerpt_is_exported_as_null(client, seed):
    seed(SEED_BASE + SEED_CANDIDATES)
    seed("UPDATE sources SET excerpt = NULL, purged_at = '2026-11-11T09:30+08:00' WHERE id = 1;")
    sources = {s["id"]: s for s in client.post(f"{API}/export").json()["tables"]["sources"]}
    assert sources[1]["excerpt"] is None
    assert MARK in sources[2]["excerpt"]


def test_sec3_export_has_no_token(export):
    assert TEST_TOKEN not in export.text


def test_ac54_export_writes_nothing(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    before = {t: count(query, t) for t in BUSINESS_TABLES}
    assert client.post(f"{API}/export").status_code == 200
    assert {t: count(query, t) for t in BUSINESS_TABLES} == before


def test_sec1_export_and_purge_require_token(app, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    with TestClient(app) as anon:
        for path, body in ((f"{API}/export", None), (f"{API}/sources/purge", {"confirm": True})):
            r = anon.post(path, json=body)
            assert r.status_code == 401
            assert r.json()["error"]["code"] == "UNAUTHORIZED"
            assert MARK not in r.text
    assert query("SELECT count(*) AS n FROM sources WHERE excerpt IS NOT NULL")[0]["n"] == 8


def test_ac54_export_includes_unpurged_raw_output(export):
    runs = export.json()["tables"]["ai_runs"]
    assert f"{MARK}RAW" in (runs[0]["raw_output"] or "")
