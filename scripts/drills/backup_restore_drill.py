"""備份還原演練（todo 13.6；#98）：用暫時資料庫走一遍 docs/deploy.md 第 6 節，不碰開發資料庫。

做的事：
1. 建來源庫 g4_drill_src：跑遷移到最新版、灌種子 SQL（預設 scripts/e2e_seeds/weekly.sql）。
2. 用正式備份工具 app.db.backup 備份（pg_dump custom 格式；保留 14 份的清理一併執行）。
3. 路徑 A：還原到全新的空資料庫 g4_drill_dst。
4. 路徑 B：在 g4_drill_dst 多寫一筆資料，再照部署文件用 `pg_restore --clean --if-exists` 覆蓋，確認回到備份內容。
5. 每條路徑都比對：每張表筆數、遷移版本、觸發器、events／rubrics 防改觸發器仍有效、序號接續（新增資料不撞號）。
結束時刪掉兩個暫時資料庫與備份檔；任一項不符以非 0 結束。

本機沒有 PostgreSQL 用戶端時，pg_dump／pg_restore 經 docker 容器執行（同 deploy.md 的 G4_PG_DUMP_CMD 例子）。

用法（在 backend/ 下）：
  .venv/bin/python ../scripts/drills/backup_restore_drill.py [種子.sql] [--container g4-pg]
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from alembic import command  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import URL, make_url  # noqa: E402

from app.config import DEFAULT_ENV_FILE, load_env_file  # noqa: E402
from app.db import backup  # noqa: E402
from tests.conftest import alembic_config  # noqa: E402

SRC, DST = "g4_drill_src", "g4_drill_dst"   # 寫死，避免動到開發資料庫
DEFAULT_SEED = BACKEND.parent / "scripts" / "e2e_seeds" / "weekly.sql"
TS = "2026-11-20T09:00+08:00"
NEW_PROJECT = text("INSERT INTO projects (name, scope, audience, created_at, updated_at) "
                   "VALUES (:name, 'work', 'manager', :ts, :ts) RETURNING id")


def admin_url() -> URL:
    load_env_file(Path(DEFAULT_ENV_FILE))
    return make_url(os.environ["G4_TEST_ADMIN_URL"])


def recreate(admin: URL, name: str, drop_only: bool = False) -> None:
    eng = create_engine(admin, isolation_level="AUTOCOMMIT")
    with eng.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        if not drop_only:
            c.execute(text(f'CREATE DATABASE "{name}"'))
    eng.dispose()


def docker_pg(container: str, admin: URL, tool: list[str], **kw) -> subprocess.CompletedProcess:
    env = ["-e", f"PGPASSWORD={admin.password or ''}"]
    return subprocess.run(["docker", "exec", "-i", *env, container, *tool, "-U", admin.username],  # noqa: S603, S607
                          check=True, **kw)


def snapshot(url: str) -> dict:
    """比對用的快照：每張表筆數、遷移版本、使用者觸發器。"""
    eng = create_engine(url)
    with eng.connect() as c:
        tables = c.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")).scalars().all()
        counts = {t: c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar_one() for t in tables}  # noqa: S608 表名來自 pg_tables
        version = c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        triggers = sorted(c.execute(text(
            "SELECT tgrelid::regclass::text || '.' || tgname FROM pg_trigger WHERE NOT tgisinternal")).scalars().all())
    eng.dispose()
    return {"counts": counts, "version": version, "triggers": triggers}


def guards_hold(url: str) -> list[str]:
    """防改觸發器仍有效、序號接續。回傳失敗項目。

    events、rubrics 的防改是列層級觸發器，表是空的時 UPDATE／DELETE 影響 0 列、不會觸發，
    所以沒有資料就判為「無法驗證」，不當作通過。
    """
    failures = []
    eng = create_engine(url)
    with eng.connect() as c:
        for table in ("events", "rubrics"):
            if c.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one() == 0:  # noqa: S608 固定表名
                failures.append(f"{table} 沒有資料，無法驗證防改觸發器（種子要含 {table}）")
    for label, sql in (("events UPDATE", "UPDATE events SET note = note"),
                       ("events DELETE", "DELETE FROM events"),
                       ("rubrics UPDATE", "UPDATE rubrics SET version = version")):
        try:
            with eng.begin() as c:
                c.execute(text(sql))
            failures.append(f"{label} 沒有被擋下")
        except Exception:   # noqa: BLE001, S110 預期被觸發器擋下
            pass
    with eng.begin() as c:   # 不指定 id 新增：序號若沒還原會撞到既有 id
        before = c.execute(text("SELECT coalesce(max(id), 0) FROM projects")).scalar_one()
        new_id = c.execute(NEW_PROJECT, {"name": "演練新增", "ts": TS}).scalar_one()
        c.execute(text("DELETE FROM projects WHERE id = :i"), {"i": new_id})
    if new_id <= before:
        failures.append(f"projects 序號沒有接續（新 id {new_id} ≤ 既有最大 {before}）")
    eng.dispose()
    return failures


def compare(label: str, expected: dict, url: str) -> list[str]:
    got = snapshot(url)
    failures = [f"{label}：{k} 不同" for k in ("version", "triggers") if got[k] != expected[k]]
    diff = {t: (expected["counts"].get(t), n) for t, n in got["counts"].items() if expected["counts"].get(t) != n}
    missing = set(expected["counts"]) - set(got["counts"])
    if diff or missing:
        failures.append(f"{label}：筆數不同 {diff}，缺表 {sorted(missing)}")
    return failures + [f"{label}：{f}" for f in guards_hold(url)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("seed", nargs="?", default=str(DEFAULT_SEED))
    ap.add_argument("--container", default="g4-pg")
    args = ap.parse_args()
    admin = admin_url()
    src_url = admin.set(database=SRC).render_as_string(hide_password=False)
    dst_url = admin.set(database=DST).render_as_string(hide_password=False)
    failures: list[str] = []
    timing: dict[str, float] = {}
    try:
        t = time.monotonic()
        recreate(admin, SRC)
        command.upgrade(alembic_config(src_url), "head")
        eng = create_engine(src_url)
        with eng.begin() as c:
            c.connection.driver_connection.cursor().execute(Path(args.seed).read_text(encoding="utf-8"))
        eng.dispose()
        expected = snapshot(src_url)
        timing["建立來源庫"] = time.monotonic() - t

        with tempfile.TemporaryDirectory() as folder:
            t = time.monotonic()
            os.environ["G4_PG_DUMP_CMD"] = (f"docker exec -e PGPASSWORD={admin.password or ''} {args.container} "
                                            f"pg_dump -U {admin.username} --format=custom {SRC}")
            dump = backup.backup(Path(folder))
            timing["備份（app.db.backup）"] = time.monotonic() - t
            size = dump.stat().st_size

            t = time.monotonic()   # 路徑 A：全新空庫
            recreate(admin, DST)
            docker_pg(args.container, admin, ["pg_restore", f"--dbname={DST}"], stdin=dump.open("rb"))
            timing["路徑 A 還原到空庫"] = time.monotonic() - t
            failures += compare("路徑 A", expected, dst_url)

            eng = create_engine(dst_url)   # 路徑 B：已有資料的庫，照 deploy.md 用 --clean 覆蓋
            with eng.begin() as c:
                c.execute(NEW_PROJECT, {"name": "還原前多出的資料", "ts": TS})
            eng.dispose()
            t = time.monotonic()
            docker_pg(args.container, admin, ["pg_restore", "--clean", "--if-exists", f"--dbname={DST}"],
                      stdin=dump.open("rb"))
            timing["路徑 B 以 --clean 覆蓋"] = time.monotonic() - t
            failures += compare("路徑 B", expected, dst_url)
    finally:
        recreate(admin, SRC, drop_only=True)
        recreate(admin, DST, drop_only=True)

    rows = sum(expected["counts"].values())
    print(f"來源：{len(expected['counts'])} 張表、{rows} 筆、遷移版本 {expected['version']}、"
          f"觸發器 {len(expected['triggers'])} 個；備份檔 {size:,} bytes")
    for k, v in timing.items():
        print(f"  {k}：{v:.2f} 秒")
    if failures:
        print("不符：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("路徑 A、B 皆一致：筆數、遷移版本、觸發器相同；events／rubrics 防改仍有效；序號接續。暫時資料庫已刪除。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
