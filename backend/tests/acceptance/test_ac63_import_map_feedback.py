"""AC-63（編號暫定）：AI-07 表頭對應的回饋寫入 ai_feedback（FR-AI-04、spec 5.6）。"""

import contextlib

import pytest

from tests.acceptance.helpers import API, count, created

TABLE = "工項SECRETHDR,PIC,起,交期\n需求確認SECRETCELL,我,2026-11-16,2026-11-18\n畫面設計,小薇,2026-11-17,2026-11-21"
AI_MAP = {"title": 0, "owner": 1, "start": 2, "end": 3}
ROWS = [
    {"index": 0, "title": "需求確認SECRETCELL", "owner": "我", "start": "2026-11-16", "end": "2026-11-18"},
    {"index": 1, "title": "畫面設計", "owner": "小薇", "start": "2026-11-17", "end": "2026-11-21"},
]


@pytest.fixture
def run_id(client, ai):
    ai.script("AI-07", AI_MAP)
    r = client.post(f"{API}/projects/import/preview", json={"text": TABLE, "target": "new", "new_name": "新專案"})
    assert r.status_code == 200, r.text
    assert r.json()["column_map"]["mapped_by"] == "ai"
    return r.json()["column_map"]["ai_run_id"]


def _commit(client, **extra):
    return client.post(f"{API}/projects/import/commit",
                       json={"target": "new", "new_name": "新專案", "rows": ROWS, **extra})


def _feedback(query):
    return query("SELECT node_id, target_type, target_id, outcome, detail FROM ai_feedback ORDER BY id")


def test_ac63_same_mapping_writes_accepted(client, run_id, query):
    body = created(_commit(client, ai_run_id=run_id, column_map=AI_MAP))
    fb = _feedback(query)
    assert len(fb) == 1
    assert (fb[0]["node_id"], fb[0]["target_type"], fb[0]["target_id"], fb[0]["outcome"]) == (
        "AI-07", "import_map", body["event_id"], "accepted")


def test_ac63_different_mapping_writes_changed(client, run_id, query):
    final = {"title": 0, "owner": None, "start": 2, "end": 3}
    created(_commit(client, ai_run_id=run_id, column_map=final))
    fb = _feedback(query)
    assert len(fb) == 1 and fb[0]["outcome"] == "changed"
    # AI 建議由伺服器從 ai_runs 取，不信前端自報
    assert fb[0]["detail"] == {"ai_run_id": run_id, "ai": AI_MAP, "final": final}


def test_ac63_detail_contains_only_column_indexes(client, run_id, query):
    created(_commit(client, ai_run_id=run_id, column_map=AI_MAP))
    detail = _feedback(query)[0]["detail"]
    assert set(detail) == {"ai_run_id", "ai", "final"}
    for part in ("ai", "final"):
        assert set(detail[part]) == {"title", "owner", "start", "end"}
        assert all(v is None or type(v) is int for v in detail[part].values())
    raw = query("SELECT CAST(detail AS text) AS d FROM ai_feedback")[0]["d"]
    assert "SECRET" not in raw and "需求確認" not in raw and "工項" not in raw


def test_ac63_second_commit_with_same_run_keeps_single_feedback(client, run_id, query):
    created(_commit(client, ai_run_id=run_id, column_map=AI_MAP))
    created(_commit(client, ai_run_id=run_id, column_map=AI_MAP))
    assert count(query, "ai_feedback") == 1
    assert count(query, "tasks") == 4  # 第二次匯入照常完成


@pytest.mark.parametrize("extra", [{"ai_run_id": "RUN"}, {"column_map": AI_MAP}])
def test_ac63_only_one_of_the_pair_is_rejected(client, run_id, query, extra):
    extra = {k: (run_id if v == "RUN" else v) for k, v in extra.items()}
    r = _commit(client, **extra)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert count(query, "tasks") == 0 and count(query, "ai_feedback") == 0 and count(query, "events") == 0


def test_ac63_unknown_run_id_is_rejected(client, run_id, query):
    r = _commit(client, ai_run_id=run_id + 999, column_map=AI_MAP)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert count(query, "tasks") == 0 and count(query, "ai_feedback") == 0


@pytest.mark.parametrize("node,status", [("AI-01", "ok"), ("AI-07", "invalid_output"), ("AI-07", "error")])
def test_ac63_run_that_is_not_an_ok_ai07_is_rejected(client, seed, query, node, status):
    seed(f"""INSERT INTO ai_runs (id, node_id, status, attempt, raw_output, created_at)
             VALUES (50, '{node}', '{status}', 1, '{{"title": 0, "owner": 1, "start": 2, "end": 3}}', '2026-11-11T09:00+08:00');""")
    r = _commit(client, ai_run_id=50, column_map=AI_MAP)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert count(query, "tasks") == 0 and count(query, "ai_feedback") == 0


def test_ac63_without_pair_imports_and_writes_no_feedback(client, run_id, query):
    created(_commit(client))
    assert count(query, "tasks") == 2
    assert count(query, "ai_feedback") == 0


def test_spec56_purged_raw_output_is_treated_as_no_run_id(client, run_id, seed, query):
    """審查 2-1、PR #20 B2：raw_output 已清除時照未帶 ai_run_id 處理。"""
    seed(f"UPDATE ai_runs SET raw_output = NULL WHERE id = {run_id};")
    created(_commit(client, ai_run_id=run_id, column_map=AI_MAP))
    assert count(query, "tasks") == 2
    assert count(query, "ai_feedback") == 0


# 測試端注入失敗：寫 ai_feedback 時資料庫丟例外。
FAIL_FEEDBACK = """
CREATE FUNCTION qc_fail_feedback() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'qc injected failure';
END;
$$;
CREATE TRIGGER qc_fail_feedback BEFORE INSERT ON ai_feedback FOR EACH ROW EXECUTE FUNCTION qc_fail_feedback();
"""


def test_spec56_feedback_failure_rolls_back_the_whole_import(client, run_id, seed, query):
    """審查 1-4：回饋與匯入在同一交易，回饋寫入失敗時一列都不留。"""
    seed(FAIL_FEEDBACK)
    status = None
    with contextlib.suppress(Exception):  # TestClient 預設會把伺服器例外往外丟
        status = _commit(client, ai_run_id=run_id, column_map=AI_MAP).status_code
    assert status is None or status >= 500
    for t in ("projects", "tasks", "events", "ai_feedback"):
        assert count(query, t) == 0, t
