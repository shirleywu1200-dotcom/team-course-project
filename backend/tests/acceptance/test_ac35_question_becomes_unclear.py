"""AC-35：問句不產生 stuck，而是待釐清；確認前任務不變（FR-INB-07 R2、FR-INB-13）。"""

from tests.acceptance.helpers import API, SEED_BASE, SEED_CANDIDATES, count, ingest

QUESTION = "[10:20] 小薇：下週測試如果環境沒好，會不會卡住？"


def _ingest_question(client, ai):
    ai.script("AI-01", {"items": [{"ref": 1, "kind": "stuck", "task_id": 3, "certainty": "sure"}]})
    r = ingest(client, QUESTION)
    assert r.status_code == 200, r.text
    return r.json()


def test_ac35_question_yields_unclear_not_stuck(client, seed, ai, query):
    seed(SEED_BASE)
    body = _ingest_question(client, ai)
    assert [c["kind"] for c in body["candidates"]] == ["unclear"]
    cand = body["candidates"][0]
    assert cand["certainty"] == "to_clarify"
    assert cand["suggest"]["kind"] == "stuck"
    assert cand["task"]["id"] == 3
    assert query("SELECT kind FROM candidates") == [{"kind": "unclear"}]


def test_ac35_task_not_blocked_before_confirmation(client, seed, ai, query):
    seed(SEED_BASE)
    _ingest_question(client, ai)
    assert query("SELECT blocked FROM tasks WHERE id = 3")[0]["blocked"] is False
    assert count(query, "events") == 0


def test_fr_inb13_clarify_applies_suggestion(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/8/clarify", json={"expected_version": 1})
    assert r.status_code == 200, r.text
    assert r.json()["candidate"]["state"] == "confirmed"
    assert query("SELECT blocked FROM tasks WHERE id = 1")[0]["blocked"] is True
    ev = query("SELECT kind, origin, origin_ref, source_id FROM events")
    assert ev == [{"kind": "status", "origin": "candidate", "origin_ref": 8, "source_id": 8}]


def test_fr_inb13_unclear_cannot_use_confirm_endpoint(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/8/confirm", json={"expected_version": 1})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert query("SELECT state FROM candidates WHERE id = 8")[0]["state"] == "open"
    assert count(query, "events") == 0


def test_fr_inb13_sure_candidate_cannot_use_clarify_endpoint(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/3/clarify", json={"expected_version": 1})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert query("SELECT blocked FROM tasks WHERE id = 3")[0]["blocked"] is False


def test_fr_inb13_ignore_unclear_keeps_record_and_task(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/8/ignore")
    assert r.status_code == 200, r.text
    assert query("SELECT state FROM candidates WHERE id = 8")[0]["state"] == "ignored"
    assert query("SELECT blocked FROM tasks WHERE id = 1")[0]["blocked"] is False
    assert count(query, "events") == 0
