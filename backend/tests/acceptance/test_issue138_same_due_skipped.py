"""#138：AI-01 判延期但新日期等於任務目前的預計完成日 → 視為沒有變動，略過並計數（FR-INB-07）。"""

from tests.acceptance.helpers import SEED_BASE, count, ingest

SAME_DAY = "[10:15] 我：API 介面定義週末會趕完"


def test_issue138_delay_to_current_due_creates_no_candidate(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", {"items": [{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "2026-11-14",
                                   "certainty": "sure"}]})
    r = ingest(client, SAME_DAY)
    assert r.status_code == 200, r.text
    assert (r.json()["result"]["created"], r.json()["result"]["skipped"]) == (0, 1)
    assert count(query, "candidates") == 0
    assert query("SELECT latest_due::text AS d FROM tasks WHERE id = 2") == [{"d": "2026-11-14"}]
    assert count(query, "events") == 0
    assert query("SELECT node_id, status FROM ai_runs") == [{"node_id": "AI-01", "status": "ok"}]
