"""Alembic 執行環境。連線字串優先取 `-x url=…`，其次取 G4_DATABASE_URL。"""

from alembic import context

from app.config import load_settings
from app.db.database import make_engine


def _url() -> str:
    url = context.get_x_argument(as_dictionary=True).get("url") or load_settings().database_url
    if not url:
        raise RuntimeError("未設定 G4_DATABASE_URL")
    return url


def run_migrations_online() -> None:
    engine = make_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
