"""FR-INB-08a（PR #20 B1）：私人專案的收件不呼叫 AI-01（資安 2）。檔名暫用，待指定 AC 編號。"""

import pytest

from app import worker
from tests.acceptance.helpers import API, MARK, SEED_BASE, ai_calls, count, ingest, lines

TEXT = f"[10:12] 我：訂機票祕密行程要延到 11/25 {MARK}"
WOULD_MATCH = {"items": [{"ref": 1, "kind": "delay", "task_id": 4, "new_due": "11/25", "certainty": "sure"}]}


def test_fr_inb08a_private_project_never_calls_ai(client, seed, ai):
    seed(SEED_BASE)
    ai.script("AI-01", WOULD_MATCH)
    r = ingest(client, TEXT, project_id=2)
    assert r.status_code == 200, r.text
    assert ai.calls == []


def test_fr_inb08a_private_project_returns_unavailable_without_ai_runs(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", WOULD_MATCH)
    body = ingest(client, TEXT, project_id=2).json()
    assert body["mode"] == "sync"
    assert body["ai_status"] == "unavailable"
    assert body["candidates"] == []
    assert count(query, "ai_runs") == 0
    assert count(query, "candidates") == 0 and count(query, "events") == 0


def test_fr_inb08a_excerpt_is_kept_and_manual_task_still_works(client, seed, ai, query):
    seed(SEED_BASE)
    ingest(client, TEXT, project_id=2)
    src = query("SELECT excerpt FROM sources")
    assert len(src) == 1 and MARK in src[0]["excerpt"]
    r = client.post(f"{API}/tasks", json={
        "title": "改訂機票", "owner": "我", "due": "2026-11-25", "scope": "private", "project_id": 2})
    assert r.status_code == 201, r.text   # spec 5.1：POST /tasks 回 201
    assert r.json()["id"]
    assert ai.calls == []


def test_fr_inb08a_private_async_job_fails_without_calling_ai(client, seed, ai, query, db):
    seed(SEED_BASE)
    r = ingest(client, lines(31, MARK), project_id=2)
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "async"
    job_id = r.json()["job_id"]
    ai.script("AI-01", WOULD_MATCH)
    for _ in range(4):
        worker.run_once(db, ai)
    job = client.get(f"{API}/ingest/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert ai.calls == []
    assert count(query, "ai_runs") == 0
    assert count(query, "candidates") == 0
    assert query("SELECT count(*) AS n FROM sources WHERE excerpt IS NOT NULL")[0]["n"] == 31
    assert MARK not in (job["error"] or "")


def test_fr_inb08a_work_project_still_calls_ai(client, seed, ai):
    """對照組：擋點只擋私人專案。"""
    seed(SEED_BASE)
    ai.script("AI-01", {"items": []})
    r = ingest(client, "[10:12] 阿德：畫面規格 v1 確定延到 11/18", project_id=1)
    assert r.status_code == 200, r.text
    assert r.json()["ai_status"] == "ok"
    assert len(ai_calls(ai, "AI-01")) == 1


@pytest.mark.xfail(reason="待裁定 Q2：排隊期間專案改為私人，以收件當下還是執行當下的範圍為準", strict=False)
def test_fr_inb08a_project_turned_private_while_queued_is_not_sent(client, seed, ai, query, db):
    seed(SEED_BASE)
    job_id = ingest(client, lines(31, MARK), project_id=1).json()["job_id"]
    seed("UPDATE projects SET scope = 'private' WHERE id = 1;")
    ai.script("AI-01", {"items": []})
    for _ in range(4):
        worker.run_once(db, ai)
    assert ai.calls == []
    assert query("SELECT status FROM jobs WHERE id = :i", i=job_id)[0]["status"] == "failed"


def test_fr_inb08a_private_job_resumed_after_restart_still_skips_ai(client, seed, ai, query, db):
    """審查 2-3(a)：私人專案的工作在服務重啟（reset_running）後續跑，仍不呼叫 AI。"""
    seed(SEED_BASE)
    job_id = ingest(client, lines(31, MARK), project_id=2).json()["job_id"]
    seed(f"UPDATE jobs SET status = 'running', attempts = 1 WHERE id = {job_id};")
    worker.reset_running(db)
    ai.script("AI-01", WOULD_MATCH)
    for _ in range(4):
        worker.run_once(db, ai)
    assert ai.calls == []
    assert count(query, "ai_runs") == 0
    assert count(query, "candidates") == 0
    assert query("SELECT status FROM jobs WHERE id = :i", i=job_id)[0]["status"] == "failed"
