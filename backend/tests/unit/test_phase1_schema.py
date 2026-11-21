"""Phase 1：DDL 約束、events 只增、遷移往返、備份（AC-11、todo 1.1–1.6）。

只用 SQL，不經任何領域程式。
"""

import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db import backup as backup_mod
from tests.conftest import alembic_config, create_empty_db, drop_db
from tests.unit.seeds import BASE, RUBRIC

FIVE = "'[\"a\",\"b\",\"c\",\"d\",\"e\"]'"
MIN_ROW = {
    "settings": {"id": "1", "energy_def_high": "'h'", "energy_def_mid": "'m'", "energy_def_low": "'l'"},
    "rubrics": {"version": "9", "levels": FIVE, "source": "'default'", "created_at": "now()"},
    "line_groups": {"name": "'g'", "kind": "'self'"},
    "projects": {"name": "'p'", "scope": "'work'", "audience": "'none'", "created_at": "now()",
                 "updated_at": "now()"},
    "goals": {"type": "'growth'", "title": "'g'", "period": "'2026Q4'", "energy_plan": "'high'",
              "created_at": "now()"},
    "tasks": {"title": "'t'", "scope": "'work'", "start_date": "'2026-11-01'", "orig_due": "'2026-11-02'",
              "latest_due": "'2026-11-02'", "created_at": "now()", "updated_at": "now()"},
    "completion_feedback": {"task_id": "2", "actual_stars": "3", "energy": "'mid'", "overdue_days": "0",
                            "rubric_id": "1", "created_at": "now()"},
    "sources": {"channel": "'paste'", "speaker": "'阿德'", "excerpt_hash": "gen_random_uuid()::text",
                "received_at": "now()", "expires_at": "now()"},
    "jobs": {"kind": "'ingest'", "status": "'queued'", "payload": "'{}'", "created_at": "now()",
             "updated_at": "now()"},
    "ai_runs": {"node_id": "'AI-01'", "status": "'ok'", "created_at": "now()"},
    "candidates": {"source_id": "1", "kind": "'delay'", "certainty": "'sure'", "created_at": "now()"},
    "batches": {"project_id": "1", "days": "3", "task_count": "1", "created_at": "now()"},
    "events": {"ts": "now()", "task_title": "''", "kind": "'task'", "field": "'x'", "origin": "'manual'"},
    "ai_feedback": {"node_id": "'AI-01'", "target_type": "'candidate'", "target_id": "1",
                    "outcome": "'accepted'", "created_at": "now()"},
    "reports": {"kind": "'weekly'", "created_at": "now()", "updated_at": "now()"},
}

# (資料表, 欄位覆寫——合法, 欄位覆寫——非法)
CHECKS = [
    ("settings", {"id": "1"}, {"id": "2"}),
    ("settings", {"default_scope": "'private'"}, {"default_scope": "'other'"}),
    ("settings", {"role": "'both'"}, {"role": "'boss'"}),
    ("settings", {"report_audience": "'client'"}, {"report_audience": "'x'"}),
    ("settings", {"confirm_cap_min": "10"}, {"confirm_cap_min": "7"}),
    ("settings", {"remind_default": "'none'"}, {"remind_default": "'noon'"}),
    ("settings", {"retention_days": "180"}, {"retention_days": "365"}),
    ("settings", {"goal_types_enabled": "'[\"growth\"]'"}, {"goal_types_enabled": "'{}'"}),
    ("rubrics", {"levels": FIVE}, {"levels": "'[\"a\",\"b\"]'"}),
    ("rubrics", {"levels": FIVE}, {"levels": "'{\"a\":1}'"}),
    ("rubrics", {"source": "'interview'"}, {"source": "'ai'"}),
    ("line_groups", {"kind": "'client'"}, {"kind": "'family'"}),
    ("line_groups", {"notified": "true", "bound": "true"}, {"notified": "false", "bound": "true"}),
    ("projects", {"name": "'名稱'"}, {"name": "'   '"}),
    ("projects", {"scope": "'private'"}, {"scope": "'x'"}),
    ("projects", {"audience": "'manager'"}, {"audience": "'x'"}),
    ("goals", {"type": "'expectation'"}, {"type": "'x'"}),
    ("goals", {"energy_plan": "'low'"}, {"energy_plan": "'x'"}),
    ("tasks", {"title": "'任務'"}, {"title": "''"}),
    ("tasks", {"scope": "'private'"}, {"scope": "'x'"}),
    ("tasks", {"status": "'doing'"}, {"status": "'x'"}),
    ("tasks", {"remind": "'eve_before'"}, {"remind": "'x'"}),
    ("tasks", {"expected_stars": "5"}, {"expected_stars": "6"}),
    ("tasks", {"expected_stars": "1"}, {"expected_stars": "0"}),
    ("tasks", {"star_source": "'import_default'"}, {"star_source": "'ai'"}),
    ("tasks", {"status": "'done'", "done_date": "'2026-11-02'"}, {"status": "'done'"}),
    ("completion_feedback", {"actual_stars": "5"}, {"actual_stars": "6"}),
    ("completion_feedback", {"energy": "'high'"}, {"energy": "'x'"}),
    ("completion_feedback", {"invest_vs_expected": "'more'"}, {"invest_vs_expected": "'x'"}),
    ("completion_feedback", {"overdue_days": "0"}, {"overdue_days": "-1"}),
    ("sources", {"channel": "'line'"}, {"channel": "'mail'"}),
    ("jobs", {"status": "'failed'"}, {"status": "'x'"}),
    ("jobs", {"kind": "'ingest'"}, {"kind": "'x'"}),
    ("ai_runs", {"node_id": "'AI-07'"}, {"node_id": "'AI-99'"}),
    ("ai_runs", {"node_id": "'AI-01'"}, {"node_id": "'AI-08'"}),   # 0002：AI-08 已取消
    ("ai_runs", {"status": "'timeout'"}, {"status": "'x'"}),
    ("candidates", {"kind": "'unmatched'"}, {"kind": "'x'"}),
    ("candidates", {"certainty": "'to_match'"}, {"certainty": "'x'"}),
    ("candidates", {"state": "'ignored'"}, {"state": "'x'"}),
    ("batches", {"days": "-3"}, {"days": "0"}),
    ("events", {"kind": "'baseline'"}, {"kind": "'x'"}),
    ("events", {"origin": "'bulk'"}, {"origin": "'x'"}),
    ("events", {"mark": "'none'"}, {"mark": "'x'"}),
    ("ai_feedback", {"outcome": "'changed'"}, {"outcome": "'x'"}),
    ("reports", {"kind": "'goal'", "goal_id": "1"}, {"kind": "'x'"}),   # 0006：goal 列要有 goal_id
]

PARENTS = BASE + RUBRIC + """
INSERT INTO sources (id, channel, speaker, excerpt_hash, received_at, expires_at)
  VALUES (1, 'paste', '阿德', 'h1', now(), now());
INSERT INTO goals (id, type, title, period, energy_plan, created_at)
  VALUES (1, 'growth', 'g', '2026Q4', 'high', now());
"""


def _insert_sql(table: str, override: dict) -> str:
    row = MIN_ROW[table] | override
    return f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join(row.values())})"  # noqa: S608


def _exec(db, sql: str):
    db.run(lambda c: c.exec_driver_sql(sql))


@pytest.mark.parametrize(("table", "ok", "bad"), CHECKS,
                         ids=[f"{t}-{'-'.join(b)}" for t, _, b in CHECKS])
def test_check_constraint_accepts_valid_and_rejects_invalid(db, seed, table, ok, bad):
    seed(PARENTS)
    if table == "settings":
        _exec(db, "DELETE FROM settings")   # 系統種子已有 id=1 那一列；settings 允許刪除，量表不允許
    with pytest.raises(IntegrityError):
        _exec(db, _insert_sql(table, bad))
    _exec(db, _insert_sql(table, ok))


def test_boolean_columns_reject_integer_literals(db, seed):
    """DA-01：SQL 種子要寫 true／false，不寫 0／1。"""
    seed(PARENTS)
    with pytest.raises(DBAPIError):
        _exec(db, _insert_sql("events", {"mine": "1"}))


@pytest.mark.parametrize("stmt", [
    "UPDATE events SET note = 'x' WHERE id = 1",
    "DELETE FROM events WHERE id = 1",
    "TRUNCATE events",
])
def test_ac11_events_are_append_only(db, seed, query, stmt):
    seed(PARENTS + "INSERT INTO events (id, ts, task_title, kind, field, origin) "
                   "VALUES (1, now(), '', 'task', 'x', 'manual');")
    with pytest.raises(DBAPIError, match="append-only"):
        _exec(db, stmt)
    assert query("SELECT note FROM events WHERE id = 1") == [{"note": None}]


def test_foreign_keys_are_enforced(db, seed):
    seed(PARENTS)
    with pytest.raises(IntegrityError):
        _exec(db, _insert_sql("tasks", {"project_id": "999"}))


def test_seed_resets_identity_sequences(db, seed, query):
    seed(PARENTS)
    _exec(db, _insert_sql("projects", {}))
    assert query("SELECT max(id) AS m FROM projects")[0]["m"] == 3


def test_migration_round_trip():
    name = f"g4_test_mig_{uuid.uuid4().hex[:8]}"
    url = create_empty_db(name)
    cfg = alembic_config(url)
    try:
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
        from sqlalchemy import create_engine
        eng = create_engine(url)
        with eng.connect() as c:
            tables = c.execute(text("SELECT count(*) FROM information_schema.tables "
                                    "WHERE table_schema = 'public' AND table_name <> 'alembic_version'")
                               ).scalar_one()
            triggers = {t: c.execute(text(f"SELECT count(*) FROM pg_trigger WHERE tgrelid = '{t}'::regclass "
                                          "AND NOT tgisinternal")).scalar_one() for t in ("events", "rubrics")}
            seeds = c.execute(text("SELECT (SELECT count(*) FROM settings), (SELECT count(*) FROM rubrics)")).one()
        eng.dispose()
        assert (tables, triggers, tuple(seeds)) == (17, {"events": 3, "rubrics": 3}, (1, 1))
    finally:
        drop_db(name)


def test_backup_keeps_latest_14(tmp_path, clock):
    from datetime import timedelta
    for _ in range(16):
        backup_mod.backup(tmp_path, dump=lambda p: p.write_bytes(b"dump"))
        clock.set(clock.now() + timedelta(days=1))
    files = sorted(tmp_path.glob("g4-*.dump"))
    assert len(files) == 14
    assert files[-1].name == "g4-20261126-100000.dump"
    assert not list(tmp_path.glob("*.partial"))


@pytest.mark.skipif(shutil.which("docker") is None, reason="需要 docker")
def test_backup_with_real_pg_dump(tmp_path, template_db):
    probe = subprocess.run(["docker", "inspect", "g4-pg"], capture_output=True)  # noqa: S603, S607
    if probe.returncode != 0:
        pytest.skip("沒有 g4-pg 容器")
    cmd = ["docker", "exec", "g4-pg", "pg_dump", "-U", "g4", "--format=custom", template_db]
    path: Path = backup_mod.backup(tmp_path, dump=lambda p: backup_mod.run_dump(p, cmd))
    assert path.read_bytes()[:5] == b"PGDMP"


# ---------- 0002、0003（PR #1 審查 A1、B2、B5） ----------

def test_ac59_seed_rows_exist_after_migrations(query):
    assert query("SELECT id, onboarded_at FROM settings") == [{"id": 1, "onboarded_at": None}]
    rubrics = query("SELECT id, version, source, jsonb_array_length(levels) AS n, levels->>0 AS first FROM rubrics")
    assert rubrics == [{"id": 1, "version": 0, "source": "default", "n": 5,
                        "first": "未達成：完成條件大部分沒有達到，需要重做或補做。"}]


def test_ac59_seed_is_idempotent_across_downgrade_and_rerun():
    name = f"g4_test_seed_{uuid.uuid4().hex[:8]}"
    url = create_empty_db(name)
    cfg = alembic_config(url)
    try:
        command.upgrade(cfg, "head")
        for target in ("0002", "0001"):
            command.downgrade(cfg, target)
            command.upgrade(cfg, "head")
        from sqlalchemy import create_engine
        eng = create_engine(url)
        seed_sql = (Path(__file__).resolve().parents[2] / "app/db/migrations/versions/0003_seed.sql").read_text(
            encoding="utf-8")
        with eng.begin() as c:
            c.connection.driver_connection.cursor().execute(seed_sql)   # 直接重跑種子
        with eng.connect() as c:
            counts = c.execute(text("SELECT (SELECT count(*) FROM settings), (SELECT count(*) FROM rubrics)")).one()
        eng.dispose()
        assert tuple(counts) == (1, 1)
    finally:
        drop_db(name)


@pytest.mark.parametrize("stmt", [
    "UPDATE rubrics SET source = 'interview' WHERE version = 0",
    "DELETE FROM rubrics WHERE version = 0",
    "TRUNCATE rubrics CASCADE",
])
def test_rubrics_are_immutable(db, query, stmt):
    with pytest.raises(DBAPIError, match="rubrics are immutable"):
        _exec(db, stmt)
    assert query("SELECT count(*) AS n FROM rubrics")[0]["n"] == 1


def test_rubrics_insert_new_version_allowed_and_settings_still_updatable(db, query):
    _exec(db, "INSERT INTO rubrics (version, levels, source, created_at) "
              "VALUES (1, '[\"a\",\"b\",\"c\",\"d\",\"e\"]', 'interview', now())")
    _exec(db, "UPDATE settings SET energy_def_low = '改過' WHERE id = 1")
    assert query("SELECT max(version) AS v FROM rubrics")[0]["v"] == 1
    assert query("SELECT energy_def_low FROM settings")[0]["energy_def_low"] == "改過"
