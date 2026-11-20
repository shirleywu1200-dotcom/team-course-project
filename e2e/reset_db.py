"""把暫時資料庫 g4_e2e 清回剛跑完遷移的狀態，再灌指定的種子 SQL（13.1；#90）。

後端（scripts/e2e_server.py）不必重啟：每個流程開始前呼叫一次，流程之間互不干擾。
只對 g4_e2e 動手；events、rubrics 的觸發器只在本交易內停用（SET LOCAL）。

用法（在 backend/ 下；Playwright 的 tests/db.ts 會自動呼叫）：
    PYTHONUTF8=1 .venv/Scripts/python ../e2e/reset_db.py [種子.sql]
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.config import DEFAULT_ENV_FILE, load_env_file  # noqa: E402

DB_NAME = "g4_e2e"   # 與 scripts/e2e_server.py 相同；寫死，避免清到開發資料庫
SYSTEM_SEED = BACKEND / "app" / "db" / "migrations" / "versions" / "0003_seed.sql"


def main() -> None:
    load_env_file(Path(DEFAULT_ENV_FILE))
    url = make_url(os.environ["G4_TEST_ADMIN_URL"]).set(database=DB_NAME)
    eng = create_engine(url)
    with eng.begin() as c:
        tables = c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                                "AND tablename <> 'alembic_version'")).scalars().all()
        c.execute(text("SET LOCAL session_replication_role = replica"))   # 停用 events、rubrics 的防改觸發器
        c.execute(text(f"TRUNCATE {', '.join(f'"{t}"' for t in tables)} RESTART IDENTITY CASCADE"))
        c.execute(text("SET LOCAL session_replication_role = origin"))
        cur = c.connection.driver_connection.cursor()
        cur.execute(SYSTEM_SEED.read_text(encoding="utf-8"))
        if sys.argv[1:]:
            cur.execute(Path(sys.argv[1]).read_text(encoding="utf-8"))
    eng.dispose()
    print(f"已重設 {DB_NAME}" + (f"，種子 {Path(sys.argv[1]).name}" if sys.argv[1:] else ""))


if __name__ == "__main__":
    main()
