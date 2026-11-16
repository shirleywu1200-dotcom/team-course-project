"""測試夾具（todo 0.7）。

- 每個測試一個獨立 PostgreSQL 資料庫，由已跑完遷移的範本資料庫複製（docs/decisions.md DA-01）。
  events 不能刪，所以不用「清表」的方式隔離。
- `seed_sql(db, sql)`：直接 INSERT 種子資料，結束時重設各表的 id 序列。
- 固定時鐘：預設「現在」是 2026-11-11 10:00（Asia/Taipei），與 spec 範例一致。

需要環境變數 G4_TEST_ADMIN_URL（可連到 postgres 管理資料庫的帳號），通常放在 env/local.env。
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.ai.client import FakeAIClient
from app.clock import TZ, Clock, FixedClock, set_clock
from app.config import DEFAULT_ENV_FILE, Settings, load_env_file
from app.db.database import Database
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DB = "g4_test_template"
TEST_TOKEN = "test-token"
DEFAULT_NOW = datetime(2026, 11, 11, 10, 0, tzinfo=TZ)

load_env_file(Path(os.environ.get("G4_ENV_FILE", DEFAULT_ENV_FILE)))


def _admin_url():
    url = os.environ.get("G4_TEST_ADMIN_URL")
    if not url:
        pytest.exit("未設定 G4_TEST_ADMIN_URL（見 env/example.env）", returncode=2)
    return make_url(url)


def _admin_engine():
    return create_engine(_admin_url(), isolation_level="AUTOCOMMIT")


def _db_url(name: str) -> str:
    return _admin_url().set(database=name).render_as_string(hide_password=False)


def alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "app/db/migrations"))
    cfg.cmd_opts = type("o", (), {"x": [f"url={url}"]})()
    return cfg


def create_empty_db(name: str) -> str:
    eng = _admin_engine()
    with eng.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        c.execute(text(f'CREATE DATABASE "{name}"'))
    eng.dispose()
    return _db_url(name)


def drop_db(name: str) -> None:
    eng = _admin_engine()
    with eng.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    eng.dispose()


@pytest.fixture(scope="session")
def template_db():
    url = create_empty_db(TEMPLATE_DB)
    command.upgrade(alembic_config(url), "head")
    yield TEMPLATE_DB
    drop_db(TEMPLATE_DB)


@pytest.fixture
def db(template_db):
    name = f"g4_test_{uuid.uuid4().hex[:10]}"
    eng = _admin_engine()
    with eng.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}" TEMPLATE "{template_db}"'))
    eng.dispose()
    database = Database(_db_url(name))
    yield database
    database.dispose()
    drop_db(name)


def seed_sql(db: Database, sql: str) -> None:
    """執行種子 SQL，之後把每張表的 id 序列設到目前最大值，避免之後的寫入撞號。"""
    def run(conn):
        raw = conn.connection.driver_connection
        with raw.cursor() as cur:
            cur.execute(sql)
            cur.execute("""
                SELECT table_name FROM information_schema.columns
                 WHERE table_schema = 'public' AND column_name = 'id' AND is_identity = 'YES'
            """)
            for (table,) in cur.fetchall():
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "  # noqa: S608 表名來自系統目錄
                    f"COALESCE((SELECT max(id) FROM {table}), 1), "
                    f"(SELECT max(id) FROM {table}) IS NOT NULL)")
    db.run(run)


@pytest.fixture
def seed(db):
    return lambda sql: seed_sql(db, sql)


@pytest.fixture(autouse=True)
def clock():
    fixed = FixedClock(DEFAULT_NOW)
    set_clock(fixed)
    yield fixed
    set_clock(Clock())


@pytest.fixture
def ai():
    return FakeAIClient()


@pytest.fixture
def app(db, ai):
    settings = Settings(database_url="unused", api_token=TEST_TOKEN, bind_host="127.0.0.1", port=0)
    return create_app(settings, db=db, ai=ai)


@pytest.fixture
def client(app):
    with TestClient(app, headers={"Authorization": f"Bearer {TEST_TOKEN}"}) as c:
        yield c


@pytest.fixture
def query(db):
    """測試用唯讀查詢：回傳 list[dict]。"""
    def q(sql: str, **params):
        return db.run(lambda c: [dict(r) for r in c.execute(text(sql), params).mappings()])
    return q
