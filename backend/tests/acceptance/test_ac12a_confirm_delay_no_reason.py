"""AC-12a：確認延期候選時，原因與註記一律為空，AI 的原因推測不被採用。

FR-AI-06 防回歸測試（todo 7.9）：由 QC 持有，不得刪除或放寬。
"""

from tests.acceptance.helpers import API, SEED_BASE, SEED_CANDIDATES, ingest


def test_ac12a_confirm_delay_reason_and_mark_are_empty(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/2/confirm", json={"expected_version": 1})
    assert r.status_code == 200, r.text
    ev = r.json()["event"]
    assert ev["kind"] == "due"
    assert ev["reason"] is None
    assert ev["mark"] is None
    row = query("SELECT reason, mark FROM events WHERE id = :i", i=ev["id"])[0]
    assert row == {"reason": None, "mark": None}


def test_ac12a_confirm_delay_uses_user_date_and_links_candidate(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/2/confirm", json={"expected_version": 1, "new_due": "2026-11-20"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["candidate"]["state"] == "confirmed"
    task = query("SELECT orig_due::text AS o, latest_due::text AS l FROM tasks WHERE id = 2")[0]
    assert task == {"o": "2026-11-14", "l": "2026-11-20"}  # 只改最新預計日（FR-DUE-02）
    ev = query("SELECT origin, origin_ref, source_id, from_value, to_value, delta_days, reason, mark "
               "FROM events WHERE id = :i", i=body["event"]["id"])[0]
    assert ev == {"origin": "candidate", "origin_ref": 2, "source_id": 2, "from_value": "2026-11-14",
                  "to_value": "2026-11-20", "delta_days": 6, "reason": None, "mark": None}
    assert query("SELECT state FROM candidates WHERE id = 2")[0]["state"] == "confirmed"


def test_ac12a_ai_reason_guess_is_not_stored_or_shown(client, seed, query, ai):
    seed(SEED_BASE)
    ai.script("AI-01", {"items": [{
        "ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/19", "certainty": "sure",
        "reason": "underestimated", "mark": "worse", "note": "AIGUESS 他低估了工作量"}]})
    r = ingest(client, "[10:15] 我：API 介面定義要延到 11/19")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ai_status"] == "ok"
    assert len(body["candidates"]) == 1
    cand = body["candidates"][0]
    assert cand["kind"] == "delay"
    assert "underestimated" not in r.text and "AIGUESS" not in r.text and "worse" not in r.text
    stored = query("SELECT CAST(row_to_json(c) AS text) AS j FROM candidates c")[0]["j"]
    assert "underestimated" not in stored and "AIGUESS" not in stored and "worse" not in stored

    r2 = client.post(f"{API}/candidates/{cand['id']}/confirm", json={"expected_version": cand["task"]["version"]})
    assert r2.status_code == 200, r2.text
    assert r2.json()["event"]["reason"] is None
    assert r2.json()["event"]["mark"] is None
    assert "AIGUESS" not in r2.text
    ev = query("SELECT reason, mark, note FROM events WHERE kind = 'due'")[0]
    assert ev["reason"] is None and ev["mark"] is None
    assert "AIGUESS" not in (ev["note"] or "")


def test_fr_ai06_clarify_delay_reason_and_mark_are_empty(client, seed, query):
    """審查 1-1：待釐清的延期候選走 clarify 寫入時，原因與註記也必須為空。"""
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/4/clarify", json={"expected_version": 1})
    assert r.status_code == 200, r.text
    ev = r.json()["event"]
    assert ev["kind"] == "due"
    assert ev["to_value"] == "2026-11-21"
    assert ev["reason"] is None
    assert ev["mark"] is None
    row = query("SELECT reason, mark, mine FROM events WHERE id = :i", i=ev["id"])[0]
    assert row == {"reason": None, "mark": None, "mine": True}


def test_fr_ai06_confirmed_delay_stays_unmarked_in_stats(client, seed):
    """系統不代填註記：確認後統計只多一筆「未註記」。"""
    seed(SEED_BASE + SEED_CANDIDATES)
    assert client.post(f"{API}/candidates/2/confirm", json={"expected_version": 1}).status_code == 200
    s = client.get(f"{API}/stats/time-management").json()
    assert s["unmarked"] == 1
    assert s["better"]["count"] == 0 and s["worse"]["count"] == 0 and s["none"] == 0
