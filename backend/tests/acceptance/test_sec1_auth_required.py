"""資安規則 1（審查 3-7、spec 5.1、5.2）：沒有 token 或 token 錯誤一律 401，本文不含資料。檔名暫用，待指定 AC 編號。"""

import pytest
from fastapi.testclient import TestClient

from tests.acceptance.helpers import API, MARK, SEED_BASE, SEED_CANDIDATES, count

SEED_JOB_AND_EVENT = """
INSERT INTO jobs (id, kind, status, attempts, payload, created_at, updated_at) VALUES
 (1, 'ingest', 'queued', 0, '{}', '2026-11-11T09:00+08:00', '2026-11-11T09:00+08:00');
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, delta_days, mine) VALUES
 (1, '2026-11-05T12:00+08:00', 1, 1, '畫面規格 v1', 'due', 'latest_due', '2026-11-12', '2026-11-13', 'manual', 1, false);
"""

CALLS = [
    ("GET", "/events", None),
    ("GET", "/candidates", None),
    ("GET", "/ingest/jobs/1", None),
    ("POST", "/ingest", {"text": f"[10:12] 阿德：畫面規格 v1 確定延到 11/18 {MARK}NEW", "project_id": 1}),
    ("POST", "/projects/import/preview", {"text": f"工項,PIC,起,交期\n{MARK}CELL,我,2026-11-16,2026-11-18", "target": "new"}),
]


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong-token"}], ids=["no-token", "wrong-token"])
@pytest.mark.parametrize("method,path,body", CALLS, ids=[f"{m} {p}" for m, p, _ in CALLS])
def test_sec1_endpoint_requires_token(app, seed, ai, query, headers, method, path, body):
    seed(SEED_BASE + SEED_CANDIDATES + SEED_JOB_AND_EVENT)
    before = {t: count(query, t) for t in ("sources", "jobs", "candidates", "ai_runs")}
    with TestClient(app, headers=headers) as anon:
        r = anon.request(method, f"{API}{path}", json=body)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"
    assert MARK not in r.text and "畫面規格" not in r.text
    assert "items" not in r.json() and "status" not in r.json()
    assert ai.calls == []
    assert {t: count(query, t) for t in before} == before
