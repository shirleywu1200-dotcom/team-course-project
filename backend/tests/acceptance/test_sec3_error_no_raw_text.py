"""資安規則 3：錯誤回應與 log 只放識別資訊，不放貼上的原文。"""

import logging

from fastapi.testclient import TestClient

from app import scheduler, worker
from app.ai.client import AIInvalidOutput, AITimeout
from tests.acceptance.helpers import API, MARK, SEED_BASE, count, ingest, lines
from tests.conftest import TEST_TOKEN

TEXT = f"[10:12] 阿德：畫面規格 v1 確定延到 11/18 {MARK}"
OK = {"items": [{"ref": 1, "kind": "delay", "task_id": 1, "new_due": "11/18", "certainty": "sure"}]}


def test_sec3_validation_error_does_not_echo_text(client, seed, query):
    seed(SEED_BASE)
    r = client.post(f"{API}/ingest", json={"text": TEXT, "project_id": "not-a-number"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert MARK not in r.text
    assert count(query, "sources") == 0


def test_sec3_unknown_project_error_does_not_echo_text(client, seed, query, ai):
    seed(SEED_BASE)
    r = ingest(client, TEXT, project_id=999)
    assert r.status_code in (404, 422)
    assert MARK not in r.text
    assert count(query, "sources") == 0
    assert ai.calls == []


def test_sec3_import_preview_error_does_not_echo_text(client):
    r = client.post(f"{API}/projects/import/preview", json={"text": f"任務,結束\n{MARK},2026-11-18", "target": "x"})
    assert r.status_code == 422
    assert MARK not in r.text


def test_sec3_logs_have_no_raw_text_on_normal_flow(client, seed, ai, caplog, db):
    """審查 3-2：收件、確認、清除全程的 log 都不含原文。"""
    seed(SEED_BASE)
    ai.script("AI-01", OK)
    with caplog.at_level(logging.DEBUG):
        body = ingest(client, TEXT).json()
        cid = body["candidates"][0]["id"]
        assert client.post(f"{API}/candidates/{cid}/confirm", json={"expected_version": 1}).status_code == 200
        client.get(f"{API}/events")
        client.post(f"{API}/export")
        scheduler.run_once(db)
        client.post(f"{API}/sources/purge", json={"confirm": True})
    assert MARK not in caplog.text


def test_sec3_logs_have_no_raw_text_on_async_flow(client, seed, ai, caplog, db):
    seed(SEED_BASE)
    with caplog.at_level(logging.DEBUG):
        ingest(client, lines(31, MARK))
        ai.script("AI-01", {"items": []})
        worker.run_once(db, ai)
    assert MARK not in caplog.text


# 測試端注入失敗：寫 sources 時資料庫丟例外，例外訊息故意帶上摘錄。
FAIL_SOURCES = """
CREATE FUNCTION qc_fail_source() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'qc boom %', NEW.excerpt;
END;
$$;
CREATE TRIGGER qc_fail_source BEFORE INSERT ON sources FOR EACH ROW EXECUTE FUNCTION qc_fail_source();
"""


def test_sec3_logs_have_no_text_cells_or_token_across_three_flows(client, seed, ai, caplog):
    """審查 3-2：收件、匯入 preview、AI-01 例外各走一次，log 全文不含貼上原文、儲存格內容與 token。"""
    seed(SEED_BASE)
    with caplog.at_level(logging.DEBUG):
        ai.script("AI-01", OK)
        assert ingest(client, TEXT).status_code == 200
        table = f"工項{MARK}HDR,PIC,起,交期\n需求確認{MARK}CELL,我,2026-11-16,2026-11-18"
        ai.script("AI-07", AIInvalidOutput(f"echo {MARK}CELL"))
        assert client.post(f"{API}/projects/import/preview", json={"text": table, "target": "new"}).status_code == 200
        assert client.post(f"{API}/projects/import/preview",
                           json={"text": table.replace("工項", "任務").replace("交期", "結束"), "target": "new"}).status_code == 200
        leak = f"provider echoed {MARK}"
        ai.script("AI-01", AITimeout(leak), AIInvalidOutput(leak), AITimeout(leak))
        assert ingest(client, f"[11:00] 小薇：首頁文案好了 {MARK}").status_code == 200
    assert MARK not in caplog.text
    assert TEST_TOKEN not in caplog.text


def test_sec3_db_failure_on_ingest_returns_fixed_internal_error(app, seed, ai, caplog, query):
    """審查 3-4（spec 5.1、5.2）：寫入丟例外時回 500 INTERNAL_ERROR，回應與 log 不含摘錄與例外內容。"""
    seed(SEED_BASE + FAIL_SOURCES)
    ai.script("AI-01", OK)
    with caplog.at_level(logging.DEBUG), TestClient(
            app, headers={"Authorization": f"Bearer {TEST_TOKEN}"}, raise_server_exceptions=False) as c:
        r = ingest(c, TEXT)
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert MARK not in r.text and "qc boom" not in r.text
    assert MARK not in caplog.text
    assert count(query, "sources") == 0 and count(query, "candidates") == 0
