"""AC-41：超過 30 行改走背景工作，狀態可查詢（FR-INB-05、spec 5.11、6.1）。"""

import pytest

from app import worker
from tests.acceptance.helpers import API, MARK, SEED_BASE, count, ingest, lines


def _job(client, job_id):
    r = client.get(f"{API}/ingest/jobs/{job_id}")
    assert r.status_code == 200, r.text
    return r.json()


def test_ac41_over_30_lines_returns_async_job(client, seed, ai, query):
    seed(SEED_BASE)
    r = ingest(client, lines(31))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "async" and body["status"] == "queued"
    assert query("SELECT id, kind, status FROM jobs") == [{"id": body["job_id"], "kind": "ingest", "status": "queued"}]
    assert ai.calls == []  # 尚未執行
    assert count(query, "candidates") == 0


def test_ac41_exactly_30_lines_is_sync(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", {"items": []})
    r = ingest(client, lines(30))
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "sync"
    assert count(query, "jobs") == 0


def test_ac41_job_status_can_be_queried(client, seed):
    seed(SEED_BASE)
    job_id = ingest(client, lines(31)).json()["job_id"]
    job = _job(client, job_id)
    assert job["status"] == "queued"
    assert job["attempts"] == 0
    assert job["result"] is None and job["error"] is None


def test_ac41_unknown_job_is_not_found(client):
    r = client.get(f"{API}/ingest/jobs/999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_ac41_worker_completes_job_and_creates_open_candidates(client, seed, ai, query, db):
    seed(SEED_BASE)
    job_id = ingest(client, "[09:00] 我：API 介面定義要延到 11/19\n" + lines(30)).json()["job_id"]
    first = query("SELECT min(id) AS i FROM sources")[0]["i"]
    ai.script("AI-01", {"items": [{"ref": first, "kind": "delay", "task_id": 2, "new_due": "11/19", "certainty": "sure"}]})
    worker.run_once(db, ai)
    job = _job(client, job_id)
    assert job["status"] == "succeeded"
    assert job["error"] is None
    assert job["result"]["created"] == 1
    assert job["result"]["duplicates"] == 0
    assert query("SELECT kind, state, task_id FROM candidates") == [{"kind": "delay", "state": "open", "task_id": 2}]
    assert count(query, "events") == 0


def test_spec61_restart_resets_running_jobs_and_keeps_attempts(client, seed, db, query):
    seed(SEED_BASE)
    job_id = ingest(client, lines(31)).json()["job_id"]
    seed(f"UPDATE jobs SET status = 'running', attempts = 1 WHERE id = {job_id};")
    worker.reset_running(db)
    assert query("SELECT status, attempts FROM jobs WHERE id = :i", i=job_id) == [{"status": "queued", "attempts": 1}]


def test_spec52_over_20000_chars_is_too_large(client, seed, query):
    seed(SEED_BASE)
    r = ingest(client, "[10:12] 阿德：" + MARK + "字" * 20000)
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert MARK not in r.text  # 資安 3
    assert count(query, "sources") == 0 and count(query, "jobs") == 0


def test_spec52_exactly_20000_chars_is_accepted(client, seed, ai):
    """審查 2-12：上限是「超過」20,000 字才拒絕。"""
    seed(SEED_BASE)
    ai.script("AI-01", {"items": []})
    prefix = "[10:12] 阿德："
    r = ingest(client, prefix + "字" * (20000 - len(prefix)))
    assert r.status_code == 200, r.text


@pytest.mark.xfail(reason="待裁定 Q6：空字串收件的行為", strict=False)
def test_ac41_empty_text_returns_zero_created(client, seed, ai, query):
    seed(SEED_BASE)
    r = ingest(client, "")
    assert r.status_code == 200, r.text
    assert r.json()["result"]["created"] == 0
    assert count(query, "sources") == 0
