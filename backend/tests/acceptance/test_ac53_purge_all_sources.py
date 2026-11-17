"""AC-53：刪除所有來源原文需要二次確認；刪除後任務、事件、候選保留（FR-GOV-03、spec 6.7、資安 5）。"""

from tests.acceptance.helpers import API, MARK, SEED_BASE, SEED_CANDIDATES, count


def _purge(client, **body):
    return client.post(f"{API}/sources/purge", json=body)


def _excerpts_left(query):
    return query("SELECT count(*) AS n FROM sources WHERE excerpt IS NOT NULL")[0]["n"]


def test_ac53_confirm_false_is_rejected(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = _purge(client, confirm=False)
    assert 400 <= r.status_code < 500
    assert _excerpts_left(query) == 8


def test_ac53_missing_confirm_is_rejected(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = _purge(client)
    assert r.status_code == 422
    assert _excerpts_left(query) == 8


def test_ac53_confirm_true_nulls_every_excerpt(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = _purge(client, confirm=True)
    assert r.status_code == 200, r.text
    assert _excerpts_left(query) == 0
    assert query("SELECT count(*) AS n FROM sources WHERE purged_at IS NULL")[0]["n"] == 0
    assert count(query, "sources") == 8  # 列還在，只清原文


def test_ac53_tasks_events_candidates_are_kept(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    assert client.post(f"{API}/candidates/2/confirm", json={"expected_version": 1}).status_code == 200
    before = {t: query(f"SELECT * FROM {t} ORDER BY id") for t in ("events", "candidates", "tasks")}
    assert _purge(client, confirm=True).status_code == 200
    assert {t: query(f"SELECT * FROM {t} ORDER BY id") for t in before} == before


def test_ac53_idempotency_cache_is_emptied(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/2/confirm", json={"expected_version": 1}, headers={"Idempotency-Key": "qc-key-1"})
    assert r.status_code == 200, r.text
    assert count(query, "idempotency_keys") == 1
    assert _purge(client, confirm=True).status_code == 200
    assert count(query, "idempotency_keys") == 0


def test_ac53_replayed_idempotency_key_does_not_return_cached_quote(client, seed):
    seed(SEED_BASE + SEED_CANDIDATES)
    body = {"expected_version": 1}
    headers = {"Idempotency-Key": "qc-key-2"}
    first = client.post(f"{API}/candidates/2/confirm", json=body, headers=headers)
    assert MARK in first.text  # 首次回應含原句
    assert _purge(client, confirm=True).status_code == 200
    again = client.post(f"{API}/candidates/2/confirm", json=body, headers=headers)
    assert MARK not in again.text


def test_ac53_api_responses_no_longer_contain_quotes(client, seed):
    seed(SEED_BASE + SEED_CANDIDATES)
    ev_id = client.post(f"{API}/candidates/2/confirm", json={"expected_version": 1}).json()["event"]["id"]
    assert _purge(client, confirm=True).status_code == 200
    events = client.get(f"{API}/events")
    item = next(i for i in events.json()["items"] if i["id"] == ev_id)
    assert item["source"]["purged"] is True and item["source"]["quote"] is None
    cands = client.get(f"{API}/candidates")
    assert all(c["quote"] is None for c in cands.json()["items"])
    for r in (events, cands, client.get(f"{API}/tasks/2"), client.get(f"{API}/projects/1/history")):
        assert r.status_code == 200
        assert MARK not in r.text


def test_ac53_export_after_purge_has_no_quote(client, seed):
    seed(SEED_BASE + SEED_CANDIDATES)
    assert _purge(client, confirm=True).status_code == 200
    r = client.post(f"{API}/export")
    assert r.status_code == 200, r.text
    assert MARK not in r.text
    assert all(s["excerpt"] is None for s in r.json()["tables"]["sources"])


def test_ac53_purge_twice_is_harmless(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    assert _purge(client, confirm=True).status_code == 200
    assert _purge(client, confirm=True).status_code == 200
    assert _excerpts_left(query) == 0
