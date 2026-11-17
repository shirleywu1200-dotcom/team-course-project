"""AC-36：含「可能、大概、應該、也許」的延期降級為待釐清（FR-INB-07 R2）。"""

import pytest

from tests.acceptance.helpers import SEED_BASE, ingest

DELAY = {"items": [{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/19", "certainty": "sure"}]}


@pytest.mark.parametrize("word", ["可能", "大概", "應該", "也許"])
def test_ac36_hedged_delay_becomes_unclear(client, seed, ai, query, word):
    seed(SEED_BASE)
    ai.script("AI-01", DELAY)
    r = ingest(client, f"[10:15] 阿德：API 介面定義{word}要延到 11/19")
    assert r.status_code == 200, r.text
    cands = r.json()["candidates"]
    assert [c["kind"] for c in cands] == ["unclear"]
    assert cands[0]["certainty"] == "to_clarify"
    assert cands[0]["suggest"] == {"kind": "delay", "new_due": "2026-11-19"}
    assert query("SELECT latest_due::text AS l FROM tasks WHERE id = 2")[0]["l"] == "2026-11-14"


def test_ac36_plain_delay_stays_delay(client, seed, ai):
    seed(SEED_BASE)
    ai.script("AI-01", DELAY)
    r = ingest(client, "[10:15] 阿德：API 介面定義確定延到 11/19")
    cands = r.json()["candidates"]
    assert [(c["kind"], c["certainty"]) for c in cands] == [("delay", "sure")]
    assert cands[0]["proposed"] == {"new_due": "2026-11-19"}
    assert cands[0]["quote"] == "API 介面定義確定延到 11/19"
    assert (cands[0]["speaker"], cands[0]["spoken_at"]) == ("阿德", "10:15")

