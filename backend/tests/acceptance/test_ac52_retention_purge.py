"""AC-52：清除排程把過期的原文設為 NULL，事件與候選保留（FR-GOV-01、spec 6.7）。"""

from app import scheduler
from tests.acceptance.helpers import API, MARK, SEED_BASE, count

# 來源 1 已過期、來源 2 未到期；各有一筆候選，來源 1 另有一筆事件。
SEED = f"""
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
 (1, 'paste', '阿德', '10:12', '畫面規格 v1 確定延到 11/18 {MARK}OLD', 'h-old', '2026-10-01T09:00+08:00', '2026-10-31T09:00+08:00'),
 (2, 'paste', '我', '10:15', 'API 介面定義要延到 11/19 {MARK}NEW', 'h-new', '2026-11-10T09:00+08:00', '2026-12-10T09:00+08:00');
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, state, created_at) VALUES
 (1, 1, 'delay', 'sure', 1, '{{"new_due":"2026-11-18"}}', 'open', '2026-10-01T09:00+08:00'),
 (2, 2, 'delay', 'sure', 2, '{{"new_due":"2026-11-19"}}', 'open', '2026-11-10T09:00+08:00');
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value,
                    origin, source_id, delta_days, mine) VALUES
 (1, '2026-10-01T10:00+08:00', 1, 1, '畫面規格 v1', 'due', 'latest_due', '2026-11-12', '2026-11-13', 'candidate', 1, 1, false);
"""
IDEM = """
INSERT INTO idempotency_keys (key, endpoint, response, created_at) VALUES
 ('k1', 'POST /api/v1/candidates/1/confirm', '{"status": 200, "body": {"quote": "原句"}}', '2026-11-11T09:30+08:00');
"""


def test_ac52_expired_excerpt_is_nulled_and_unexpired_kept(seed, db, query):
    seed(SEED_BASE + SEED)
    scheduler.run_once(db)
    rows = query("SELECT id, excerpt, purged_at IS NOT NULL AS purged FROM sources ORDER BY id")
    assert rows[0] == {"id": 1, "excerpt": None, "purged": True}
    assert rows[1]["purged"] is False and f"{MARK}NEW" in rows[1]["excerpt"]


def test_ac52_events_candidates_tasks_untouched(seed, db, query):
    seed(SEED_BASE + SEED)
    before = {t: query(f"SELECT * FROM {t} ORDER BY id") for t in ("events", "candidates", "tasks")}
    scheduler.run_once(db)
    assert {t: query(f"SELECT * FROM {t} ORDER BY id") for t in before} == before


def test_ac52_idempotency_keys_removed_when_something_is_purged(seed, db, query):
    seed(SEED_BASE + SEED + IDEM)
    scheduler.run_once(db)
    assert count(query, "idempotency_keys") == 0


def test_ac52_purge_is_idempotent(seed, db, query):
    seed(SEED_BASE + SEED)
    scheduler.run_once(db)
    first = query("SELECT * FROM sources ORDER BY id")
    scheduler.run_once(db)
    assert query("SELECT * FROM sources ORDER BY id") == first


def test_ac52_candidate_remains_listed_with_null_quote(client, seed, db):
    seed(SEED_BASE + SEED)
    scheduler.run_once(db)
    r = client.get(f"{API}/candidates", params={"state": "open"})
    assert r.status_code == 200, r.text
    by_id = {c["id"]: c for c in r.json()["items"]}
    assert set(by_id) == {1, 2}
    assert by_id[1]["quote"] is None
    assert f"{MARK}NEW" in by_id[2]["quote"]
    assert f"{MARK}OLD" not in r.text


def test_spec67_changing_retention_recalculates_unpurged_expiry(client, seed, db, query):
    seed(SEED_BASE + SEED)
    scheduler.run_once(db)  # 先清掉來源 1
    r = client.put(f"{API}/settings", json={"retention_days": 90})
    assert r.status_code == 200, r.text
    rows = query("SELECT id, (expires_at - received_at) = interval '90 days' AS ok, excerpt FROM sources ORDER BY id")
    assert rows[1]["ok"] is True
    assert rows[0]["excerpt"] is None  # 已清除的不會復原


def test_spec67_longer_retention_saves_not_yet_purged_source(client, seed, db, query):
    """來源 1 以 30 天算已過期，但清除前把期限改為 90 天，就不該被清。"""
    seed(SEED_BASE + SEED)
    assert client.put(f"{API}/settings", json={"retention_days": 90}).status_code == 200
    scheduler.run_once(db)
    assert query("SELECT excerpt IS NOT NULL AS kept FROM sources WHERE id = 1")[0]["kept"] is True


# 保存期限 90 天；來源與 AI 紀錄都是 40 天前（2026-10-02）的。
SEED_40_DAYS_OLD = f"""
UPDATE settings SET retention_days = 90;
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
 (1, 'paste', '阿德', '10:12', '畫面規格 v1 確定延到 11/18 {MARK}SRC', 'h-40', '2026-10-02T09:00+08:00', '2026-12-31T09:00+08:00');
INSERT INTO ai_runs (id, node_id, status, attempt, raw_output, created_at) VALUES
 (1, 'AI-01', 'ok', 1, '{{"items": [], "echo": "{MARK}RAW"}}', '2026-10-02T09:00+08:00');
"""
SEED_UNEXPIRED_ONLY = f"""
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
 (2, 'paste', '我', '10:15', 'API 介面定義要延到 11/19 {MARK}NEW', 'h-new', '2026-11-10T09:00+08:00', '2026-12-10T09:00+08:00');
"""


def test_spec67_shortening_retention_purges_excerpt_and_raw_output(client, seed, db, query):
    """審查 2-4：90 天改為 30 天後，40 天前的原文與 raw_output 都要在下次排程清掉。"""
    seed(SEED_BASE + SEED_40_DAYS_OLD)
    scheduler.run_once(db)  # 對照：90 天時都還在
    assert query("SELECT excerpt FROM sources")[0]["excerpt"] is not None
    assert query("SELECT raw_output FROM ai_runs")[0]["raw_output"] is not None
    assert client.put(f"{API}/settings", json={"retention_days": 30}).status_code == 200
    scheduler.run_once(db)
    src = query("SELECT excerpt, purged_at FROM sources")[0]
    assert src["excerpt"] is None and src["purged_at"] is not None
    assert query("SELECT raw_output FROM ai_runs")[0]["raw_output"] is None


def test_spec67_fresh_idempotency_key_survives_when_nothing_is_purged(seed, db, query):
    """審查 2-5：沒有原文被清除時，未滿 24 小時的重送暫存不該被刪。"""
    seed(SEED_BASE + SEED_UNEXPIRED_ONLY + IDEM)
    scheduler.run_once(db)
    assert query("SELECT key FROM idempotency_keys") == [{"key": "k1"}]
    assert query("SELECT excerpt IS NOT NULL AS kept FROM sources")[0]["kept"] is True
