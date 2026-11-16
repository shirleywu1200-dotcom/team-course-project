"""FR-IMP-02（審查 1-3）：匯入目標是私人範圍的既有專案時不呼叫 AI-07（資安 2）。檔名暫用，待指定 AC 編號。"""

from tests.acceptance.helpers import API, SEED_BASE, ai_calls, count

TABLE = "工項,PIC,起,交期\n訂飯店,我,2026-11-16,2026-11-18"
AI_MAP = {"title": 0, "owner": 1, "start": 2, "end": 3}


def _preview(client, target, **extra):
    r = client.post(f"{API}/projects/import/preview", json={"text": TABLE, "target": target, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def test_fr_imp02_private_target_does_not_call_ai07(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-07", AI_MAP)
    body = _preview(client, 2)
    assert ai.calls == []
    assert count(query, "ai_runs") == 0
    assert body["ai_status"] == "unavailable"
    assert body["column_map"]["mapped_by"] is None


def test_fr_imp02_private_target_accepts_manual_column_map(client, seed, ai):
    seed(SEED_BASE)
    body = _preview(client, 2, column_map=AI_MAP)
    assert ai.calls == []
    assert body["column_map"]["mapped_by"] == "manual"
    assert body["rows"][0]["title"] == "訂飯店"


def test_fr_imp02_work_target_still_calls_ai07(client, seed, ai):
    """對照組：擋點只擋私人專案。"""
    seed(SEED_BASE)
    ai.script("AI-07", AI_MAP)
    body = _preview(client, 1)
    assert len(ai_calls(ai, "AI-07")) == 1
    assert body["column_map"]["mapped_by"] == "ai"


def test_fr_imp02_private_target_with_standard_header_uses_rule(client, seed, ai):
    seed(SEED_BASE)
    r = client.post(f"{API}/projects/import/preview",
                    json={"text": "任務,負責人,開始,結束\n訂飯店,我,2026-11-16,2026-11-18", "target": 2})
    assert r.status_code == 200, r.text
    assert r.json()["column_map"]["mapped_by"] == "rule"
    assert ai.calls == []
