"""Phase 10 第二段：遷移 0004（reports 的 ai_items、ai_status、每週一列、週次 CHECK）。

依 spec 4.2.1 與 #18 第 1 點 (b)、J8。
"""

import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import alembic_config, create_empty_db, drop_db

NOW = "'2026-11-11T10:00+08:00'"


def insert(db, kind, period, ai_status="NULL"):
    db.run(lambda c: c.execute(text(
        f"INSERT INTO reports (kind, period_start, ai_status, created_at, updated_at) "  # noqa: S608 測試固定字串
        f"VALUES ('{kind}', {period}, {ai_status}, {NOW}, {NOW})")))


def test_one_weekly_row_per_week(db):
    insert(db, "weekly", "'2026-11-09'")
    with pytest.raises(IntegrityError):
        insert(db, "weekly", "'2026-11-09'")


def test_goal_reports_share_period_freely(db):
    insert(db, "weekly", "'2026-11-09'")
    insert(db, "goal", "'2026-11-09'")
    insert(db, "goal", "'2026-11-09'")


def test_ai_status_check(db):
    insert(db, "weekly", "'2026-11-09'", "'ok'")
    with pytest.raises(IntegrityError):
        insert(db, "weekly", "'2026-11-16'", "'timeout'")


def test_weekly_row_needs_period(db):
    with pytest.raises(IntegrityError):
        insert(db, "weekly", "NULL")
    insert(db, "goal", "NULL")   # 目標回報不受限


def test_ai_items_is_jsonb(db, query):
    db.run(lambda c: c.execute(text(
        "INSERT INTO reports (kind, period_start, ai_items, created_at, updated_at) "
        "VALUES ('weekly', '2026-11-09', CAST(:j AS jsonb), now(), now())"),
        {"j": '[{"section": "next", "task_id": 1, "event_id": null}]'}))
    assert query("SELECT ai_items FROM reports")[0]["ai_items"] == [{"section": "next", "task_id": 1, "event_id": None}]


def test_0004_downgrade_and_upgrade_with_data():
    name = f"g4_test_0004_{uuid.uuid4().hex[:8]}"
    url = create_empty_db(name)
    cfg = alembic_config(url)
    eng = create_engine(url)
    try:
        command.upgrade(cfg, "0003")
        with eng.begin() as c:
            c.execute(text("INSERT INTO reports (kind, period_start, created_at, updated_at) "
                           "VALUES ('weekly', '2026-11-09', now(), now())"))
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "0003")
        with eng.connect() as c:
            cols = set(c.execute(text("SELECT column_name FROM information_schema.columns "
                                      "WHERE table_name = 'reports'")).scalars())
            idx = c.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = 'reports_weekly_period_uq'")
                            ).scalar_one()
        assert not {"ai_items", "ai_status"} & cols and idx == 0
        command.upgrade(cfg, "head")
        with eng.connect() as c:
            row = c.execute(text("SELECT ai_items, ai_status FROM reports")).one()
        assert tuple(row) == (None, None)
    finally:
        eng.dispose()
        drop_db(name)
