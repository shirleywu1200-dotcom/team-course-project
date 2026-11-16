"""遷移 0004：candidates.project_id（PR #20 審查 B5；spec 4.2.1）。"""

import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import alembic_config, create_empty_db, drop_db
from tests.unit.seeds import BASE

SOURCE = """
INSERT INTO sources (id, channel, speaker, excerpt_hash, received_at, expires_at)
  VALUES (1, 'paste', '阿德', 'h1', now(), now());
"""


def add_candidate(db, project_id):
    db.run(lambda c: c.execute(text(
        "INSERT INTO candidates (source_id, kind, certainty, project_id, created_at) "
        "VALUES (1, 'unmatched', 'to_match', :p, now())"), {"p": project_id}))


def test_project_id_is_optional_and_references_projects(db, seed, query):
    seed(BASE + SOURCE)
    add_candidate(db, None)
    add_candidate(db, 1)
    assert [r["project_id"] for r in query("SELECT project_id FROM candidates ORDER BY id")] == [None, 1]
    with pytest.raises(IntegrityError):
        add_candidate(db, 999)


def test_project_id_is_indexed(query):
    assert query("SELECT count(*) AS n FROM pg_indexes WHERE indexname = 'ix_candidates_project'")[0]["n"] == 1


def test_0004_downgrade_and_upgrade_with_data():
    name = f"g4_test_0004c_{uuid.uuid4().hex[:8]}"
    url = create_empty_db(name)
    cfg = alembic_config(url)
    eng = create_engine(url)
    try:
        command.upgrade(cfg, "head")
        with eng.begin() as c:
            c.connection.driver_connection.cursor().execute(BASE + SOURCE)
            c.execute(text("INSERT INTO candidates (source_id, kind, certainty, project_id, created_at) "
                           "VALUES (1, 'unmatched', 'to_match', 1, now())"))
        command.downgrade(cfg, "0003")
        with eng.connect() as c:
            cols = set(c.execute(text("SELECT column_name FROM information_schema.columns "
                                      "WHERE table_name = 'candidates'")).scalars())
        assert "project_id" not in cols
        command.upgrade(cfg, "head")
        with eng.connect() as c:
            assert c.execute(text("SELECT project_id FROM candidates")).scalar_one() is None
    finally:
        eng.dispose()
        drop_db(name)
