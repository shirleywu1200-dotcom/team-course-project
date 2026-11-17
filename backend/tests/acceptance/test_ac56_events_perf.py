"""AC-56：1,000 個任務、10,000 筆事件時，GET /events（含篩選）在 300 ms 內回應。

量測方式（spec 標〔假設〕，未定義）：先暖機一次，再取 3 次中最快的一次。
"""

import time

import pytest

from tests.acceptance.helpers import API

SEED = """
INSERT INTO projects (id, name, scope, audience, created_at, updated_at)
SELECT g, '專案 ' || g, 'work', 'manager', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00' FROM generate_series(1, 10) g;
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, created_at, updated_at)
SELECT g, CASE WHEN g % 10 = 0 THEN NULL ELSE g % 10 END, '任務 ' || g, CASE WHEN g % 2 = 0 THEN '我' ELSE '阿德' END,
       'work', '2026-11-01', '2026-11-20', '2026-11-22', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00'
FROM generate_series(1, 1000) g;
INSERT INTO events (ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, delta_days, mine)
SELECT timestamptz '2026-10-01T09:00+08:00' + (g || ' minutes')::interval,
       CASE WHEN (g % 1000 + 1) % 10 = 0 THEN NULL ELSE (g % 1000 + 1) % 10 END, g % 1000 + 1, '任務 ' || (g % 1000 + 1),
       CASE WHEN g % 3 = 0 THEN 'status' ELSE 'due' END, CASE WHEN g % 3 = 0 THEN 'status' ELSE 'latest_due' END,
       '2026-11-20', '2026-11-22', 'manual', CASE WHEN g % 3 = 0 THEN NULL ELSE 2 END, (g % 1000 + 1) % 2 = 0
FROM generate_series(1, 10000) g;
"""


@pytest.fixture
def big(seed, query):
    seed(SEED)
    assert query("SELECT count(*) AS n FROM tasks")[0]["n"] == 1000
    assert query("SELECT count(*) AS n FROM events")[0]["n"] == 10000


def _best_ms(client, params):
    client.get(f"{API}/events", params=params)  # 暖機
    best = None
    for _ in range(3):
        start = time.perf_counter()
        r = client.get(f"{API}/events", params=params)
        ms = (time.perf_counter() - start) * 1000
        assert r.status_code == 200, r.text
        best = ms if best is None else min(best, ms)
    return best, r.json()


def test_ac56_events_default_query_within_300ms(client, big):
    ms, body = _best_ms(client, {})
    assert body["total"] == 10000
    assert len(body["items"]) == 100
    assert ms < 300, f"{ms:.0f} ms"


def test_ac56_events_filtered_query_within_300ms(client, big):
    ms, body = _best_ms(client, {"project_id": 3, "kind": "due", "task_id": 13})
    assert body["total"] > 0
    assert all((i["project_id"], i["kind"], i["task_id"]) == (3, "due", 13) for i in body["items"])
    assert ms < 300, f"{ms:.0f} ms"


def test_ac56_events_max_page_within_300ms(client, big):
    ms, body = _best_ms(client, {"project_id": "none", "limit": 500})
    assert len(body["items"]) == 500
    assert ms < 300, f"{ms:.0f} ms"
