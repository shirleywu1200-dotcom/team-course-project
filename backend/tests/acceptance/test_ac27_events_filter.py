"""AC-27：歷程查詢的篩選組合與 total（FR-HIS-03、spec 5.8）。"""

import pytest

from tests.acceptance.helpers import API, SEED_BASE

# 事件 1–4、8 屬專案 1；5 屬專案 3；6、7 屬單點任務 9。事件 3、4 同一批次。
SEED_EVENTS = """
INSERT INTO batches (id, project_id, days, task_count, created_at) VALUES (1, 1, 3, 2, '2026-11-07T12:00+08:00');
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value,
                    origin, delta_days, mark, mine, batch_id) VALUES
 (1, '2026-11-05T12:00+08:00', 1, 1, '畫面規格 v1', 'due', 'latest_due', '2026-11-12', '2026-11-13', 'manual', 1, NULL, false, NULL),
 (2, '2026-11-06T12:00+08:00', 1, 1, '畫面規格 v1', 'status', 'blocked', 'false', 'true', 'manual', NULL, NULL, false, NULL),
 (3, '2026-11-07T12:00+08:00', 1, 2, 'API 介面定義', 'due', 'latest_due', '2026-11-11', '2026-11-14', 'bulk', 3, 'none', true, 1),
 (4, '2026-11-08T12:00+08:00', 1, 3, '測試環境建置', 'due', 'latest_due', '2026-11-17', '2026-11-20', 'bulk', 3, 'none', true, 1),
 (5, '2026-11-09T12:00+08:00', 3, 8, '首頁文案', 'due', 'latest_due', '2026-11-19', '2026-11-20', 'manual', 1, NULL, false, NULL),
 (6, '2026-11-10T12:00+08:00', NULL, 9, '報帳', 'due', 'latest_due', '2026-11-19', '2026-11-20', 'manual', 1, 'worse', true, NULL),
 (7, '2026-11-10T13:00+08:00', NULL, 9, '報帳', 'task', 'owner_name', '阿德', '我', 'manual', NULL, NULL, true, NULL),
 (8, '2026-11-11T09:00+08:00', 1, NULL, '', 'project', 'name', '會員系統', '會員系統 2.0 改版', 'manual', NULL, NULL, false, NULL);
"""


def _ids(client, path=f"{API}/events", **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text
    body = r.json()
    return sorted(i["id"] for i in body["items"]), body["total"]


@pytest.fixture
def data(seed):
    seed(SEED_BASE + SEED_EVENTS)


def test_ac27_filter_by_project(client, data):
    assert _ids(client, project_id=1) == ([1, 2, 3, 4, 8], 5)


def test_ac27_filter_by_project_and_kind(client, data):
    assert _ids(client, project_id=1, kind="due") == ([1, 3, 4], 3)


def test_ac27_filter_by_project_kind_and_task(client, data):
    assert _ids(client, project_id=1, kind="due", task_id=1) == ([1], 1)


def test_ac27_filter_by_task_only(client, data):
    assert _ids(client, task_id=1) == ([1, 2], 2)


def test_ac27_project_none_returns_only_standalone_task_events(client, data):
    ids, total = _ids(client, project_id="none")
    assert (ids, total) == ([6, 7], 2)
    assert _ids(client, project_id="none", kind="due") == ([6], 1)


def test_ac27_no_match_returns_empty_and_zero_total(client, data):
    assert _ids(client, project_id=3, kind="status") == ([], 0)


def test_ac27_total_ignores_limit_and_offset(client, data):
    r = client.get(f"{API}/events", params={"project_id": 1, "limit": 2, "offset": 1})
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 2
    assert r.json()["total"] == 5


def test_ac27_project_history_equals_events_with_project_id(client, data):
    assert _ids(client, f"{API}/projects/1/history") == _ids(client, project_id=1)
    assert _ids(client, f"{API}/projects/1/history", kind="due") == ([1, 3, 4], 3)


def test_fr_blk08_filter_by_batch(client, data):
    assert _ids(client, batch_id=1) == ([3, 4], 2)


def test_ac27_filter_by_from_and_to(client, data):
    """審查 1-11：from、to 兩端都含當天。"""
    assert _ids(client, **{"from": "2026-11-07", "to": "2026-11-08"}) == ([3, 4], 2)
    assert _ids(client, **{"from": "2026-11-10"}) == ([6, 7, 8], 3)
    assert _ids(client, to="2026-11-05") == ([1], 1)


def test_ac27_unknown_kind_is_rejected(client, data):
    assert client.get(f"{API}/events", params={"kind": "nope"}).status_code == 422


def test_ac27_limit_500_is_accepted(client, data):
    assert client.get(f"{API}/events", params={"limit": 500}).status_code == 200


def test_ac27_limit_over_500_is_rejected(client, data):
    assert client.get(f"{API}/events", params={"limit": 501}).status_code == 422
