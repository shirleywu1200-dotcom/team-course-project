"""前端真實瀏覽器走查用的暫時後端（不碰開發資料庫）。

做的事：用 G4_TEST_ADMIN_URL 重建暫時資料庫 g4_e2e → 跑遷移 → 執行種子 SQL（選填）→ 以測試 token 啟動後端（port 8000）。
AI 為不可用的假實作（與 app.main.run 相同）。走查完執行 `--drop` 刪庫。

用法（在 backend/ 下）：
  PYTHONUTF8=1 .venv/Scripts/python ../scripts/e2e_server.py [種子.sql]    # 啟動
  PYTHONUTF8=1 .venv/Scripts/python ../scripts/e2e_server.py --drop        # 刪庫
另開終端機 `cd frontend && npx vite --port 5173`，瀏覽器開 http://127.0.0.1:5173，token 填 e2e-local-token。
收尾：Vite 由 npx 啟動的 node 子行程要另外結束，否則 5173 會被佔住。
種子範例：scripts/e2e_seeds/inbox.sql（12.8 收件匣）。
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from alembic import command
from app.config import DEFAULT_ENV_FILE, load_env_file
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from tests.conftest import alembic_config

DB_NAME = "g4_e2e"
TOKEN = "e2e-local-token"   # 只用於本機暫時資料庫的測試值


def recreate(admin, drop_only: bool) -> None:
    eng = create_engine(admin, isolation_level="AUTOCOMMIT")
    with eng.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{DB_NAME}" WITH (FORCE)'))
        if not drop_only:
            c.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
    eng.dispose()


def main() -> None:
    load_env_file(Path(DEFAULT_ENV_FILE))
    admin = make_url(os.environ["G4_TEST_ADMIN_URL"])
    if sys.argv[1:] == ["--drop"]:
        recreate(admin, drop_only=True)
        print(f"已刪除 {DB_NAME}")
        return
    recreate(admin, drop_only=False)
    url = admin.set(database=DB_NAME).render_as_string(hide_password=False)
    command.upgrade(alembic_config(url), "head")
    if sys.argv[1:]:
        eng = create_engine(url)
        with eng.begin() as c:
            c.connection.driver_connection.cursor().execute(Path(sys.argv[1]).read_text(encoding="utf-8"))
        eng.dispose()

    os.environ["G4_DATABASE_URL"] = url
    os.environ["G4_API_TOKEN"] = TOKEN
    os.environ["G4_PORT"] = "8000"
    from app.main import run

    run()


if __name__ == "__main__":
    main()
