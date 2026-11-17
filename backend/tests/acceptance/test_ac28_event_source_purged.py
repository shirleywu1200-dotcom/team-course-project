"""AC-28：來源原文過期被清除後，事件仍在，原句顯示為已刪除（FR-HIS-05、資安 5）。"""

from app import scheduler
from tests.acceptance.helpers import API, MARK, SEED_BASE

# 來源 1 已過保存期限、來源 2 尚未到期；事件 1、2 各引用一則。
SEED = f"""
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
 (1, 'paste', '阿德', '10:12', '畫面規格 v1 確定延到 11/13 {MARK}OLD', 'h-old', '2026-10-01T09:00+08:00', '2026-10-31T09:00+08:00'),
 (2, 'paste', '我', '10:15', 'API 介面定義延到 11/14 {MARK}NEW', 'h-new', '2026-11-10T09:00+08:00', '2026-12-10T09:00+08:00');
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, state, decision, decided_at, created_at) VALUES
 (1, 1, 'delay', 'sure', 1, '{{"new_due":"2026-11-13"}}', 'confirmed', 'confirm', '2026-10-01T10:00+08:00', '2026-10-01T09:00+08:00'),
 (2, 2, 'delay', 'sure', 2, '{{"new_due":"2026-11-14"}}', 'confirmed', 'confirm', '2026-11-10T10:00+08:00', '2026-11-10T09:00+08:00');
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value,
                    origin, origin_ref, source_id, delta_days, mine) VALUES
 (1, '2026-10-01T10:00+08:00', 1, 1, '畫面規格 v1', 'due', 'latest_due', '2026-11-12', '2026-11-13', 'candidate', 1, 1, 1, false),
 (2, '2026-11-10T10:00+08:00', 1, 2, 'API 介面定義', 'due', 'latest_due', '2026-11-13', '2026-11-14', 'candidate', 2, 2, 1, true);
"""


def _event(client, event_id):
    items = client.get(f"{API}/events", params={"project_id": 1}).json()["items"]
    return next(i for i in items if i["id"] == event_id)


def test_ac28_before_purge_quote_is_shown(client, seed):
    seed(SEED_BASE + SEED)
    src = _event(client, 1)["source"]
    assert src["purged"] is False
    assert MARK in src["quote"]


def test_ac28_after_retention_purge_event_remains_with_purged_source(client, seed, db):
    seed(SEED_BASE + SEED)
    scheduler.run_once(db)
    r = client.get(f"{API}/events", params={"project_id": 1})
    assert r.json()["total"] == 2
    assert _event(client, 1)["source"]["purged"] is True
    assert _event(client, 1)["source"]["quote"] is None
    assert f"{MARK}OLD" not in r.text
    # 未到期的來源不受影響
    assert _event(client, 2)["source"]["purged"] is False
    assert f"{MARK}NEW" in _event(client, 2)["source"]["quote"]


def test_ac28_event_rows_unchanged_by_purge(seed, db, query):
    seed(SEED_BASE + SEED)
    before = query("SELECT * FROM events ORDER BY id")
    scheduler.run_once(db)
    assert query("SELECT * FROM events ORDER BY id") == before


def test_ac28_task_detail_history_hides_purged_quote(client, seed, db):
    seed(SEED_BASE + SEED)
    scheduler.run_once(db)
    r = client.get(f"{API}/tasks/1")
    assert r.status_code == 200, r.text
    assert f"{MARK}OLD" not in r.text
