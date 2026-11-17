"""AC-40：AI-01 不合格式或逾時時重試至多 2 次，仍失敗則保留摘錄、不寫候選與事件（FR-INB-08）。"""

import logging

from app import worker
from app.ai.client import AIInvalidOutput, AITimeout
from tests.acceptance.helpers import API, MARK, SEED_BASE, ai_calls, count, ingest, lines

TEXT = f"[10:15] 我：API 介面定義要延到 11/19 {MARK}"
OK = {"items": [{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/19", "certainty": "sure"}]}


def test_ac40_invalid_output_retries_twice_then_stops(client, seed, ai):
    seed(SEED_BASE)
    ai.script("AI-01", AIInvalidOutput(), AIInvalidOutput(), AIInvalidOutput(), OK)
    r = ingest(client, TEXT)
    assert r.status_code == 200, r.text
    assert len(ai_calls(ai, "AI-01")) == 3  # 首次＋重試 2 次
    assert r.json()["ai_status"] == "invalid_output"


def test_ac40_invalid_output_writes_no_candidate_or_event_and_keeps_excerpt(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", AIInvalidOutput(), AIInvalidOutput(), AIInvalidOutput())
    r = ingest(client, TEXT)
    assert r.status_code == 200, r.text
    assert r.json()["candidates"] == []
    assert count(query, "candidates") == 0
    assert count(query, "events") == 0
    src = query("SELECT excerpt FROM sources")
    assert len(src) == 1 and MARK in src[0]["excerpt"]


def test_ac40_output_without_items_counts_as_invalid(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", {"foo": 1}, {"foo": 1}, {"foo": 1})
    r = ingest(client, TEXT)
    assert r.status_code == 200, r.text
    assert r.json()["ai_status"] == "invalid_output"
    assert count(query, "candidates") == 0


def test_ac40_third_attempt_succeeds(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", AIInvalidOutput(), AIInvalidOutput(), OK)
    r = ingest(client, TEXT)
    assert r.status_code == 200, r.text
    assert r.json()["ai_status"] == "ok"
    assert r.json()["result"]["created"] == 1
    assert count(query, "candidates") == 1


def test_ac40_timeout_degrades_to_unavailable(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", AITimeout(), AITimeout(), AITimeout())
    r = ingest(client, TEXT)
    assert r.status_code == 200, r.text  # spec 5.3：降級仍回 200
    assert r.json()["ai_status"] == "unavailable"
    assert count(query, "candidates") == 0 and count(query, "events") == 0
    assert query("SELECT excerpt FROM sources")[0]["excerpt"] is not None


def test_fr_ai02_each_attempt_recorded_in_ai_runs(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", AIInvalidOutput(), AIInvalidOutput(), OK)
    assert ingest(client, TEXT).status_code == 200
    runs = query("SELECT node_id, status, attempt FROM ai_runs ORDER BY id")
    assert [r["node_id"] for r in runs] == ["AI-01"] * 3
    assert [r["status"] for r in runs] == ["invalid_output", "invalid_output", "ok"]
    assert [r["attempt"] for r in runs] == [1, 2, 3]


def test_sec3_ai_error_text_not_stored_or_returned(client, seed, ai, query, caplog):
    """資安 3：例外訊息即使含原文，也不進 ai_runs.error、回應或 log。"""
    seed(SEED_BASE)
    leak = f"provider echoed: {TEXT}"
    ai.script("AI-01", AITimeout(leak), AIInvalidOutput(leak), AITimeout(leak))
    with caplog.at_level(logging.DEBUG):
        r = ingest(client, TEXT)
    assert r.status_code == 200, r.text
    assert MARK not in r.text
    for row in query("SELECT error FROM ai_runs"):
        assert MARK not in (row["error"] or "")
    assert MARK not in caplog.text


def test_ac40_async_job_fails_after_retries_and_keeps_excerpts(client, seed, ai, query, db):
    seed(SEED_BASE)
    r = ingest(client, lines(31, MARK))
    assert r.status_code == 200 and r.json()["mode"] == "async", r.text
    job_id = r.json()["job_id"]
    ai.script("AI-01", *[AIInvalidOutput(f"echo {MARK}") for _ in range(6)])
    for _ in range(6):
        worker.run_once(db, ai)
        if query("SELECT status FROM jobs WHERE id = :i", i=job_id)[0]["status"] in ("failed", "succeeded"):
            break
    job = client.get(f"{API}/ingest/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert job["error"]  # 可顯示訊息
    assert MARK not in job["error"]
    assert len(ai_calls(ai, "AI-01")) == 3
    assert count(query, "candidates") == 0 and count(query, "events") == 0
    assert query("SELECT count(*) AS n FROM sources WHERE excerpt IS NOT NULL")[0]["n"] == 31
    assert MARK not in (query("SELECT error FROM jobs WHERE id = :i", i=job_id)[0]["error"] or "")
