"""例外演練（todo 13.5；#98）：真實行程、暫時資料庫，驗證 spec 6.1、7 與 AC-57。不碰開發資料庫。

情境：
  A 重啟時有 running 工作：背景工作處理到一半（寫 ai_runs 時被鎖住）時 SIGKILL 行程，
    重啟後工作要改回 queued 續跑完，attempts 保留（spec 6.1）。
  B 寫入中途崩潰：整批順延 commit 已寫入 batch、卡在寫事件時 SIGKILL 行程，
    事件、任務、batch 都不能只寫一半（AC-57）；重啟後同一請求可正常完成。
  C 資料庫鎖定：
    C1 任務列被另一連線鎖住 → 改期請求等待，鎖放開後完成，只寫一筆事件。
    C2 鎖住期間對方改了任務版本 → 改期請求回 STALE_VERSION，不寫入（spec 7 樂觀鎖）。
    C3 死結 → 服務端被選為犧牲者（40P01）後整筆重試並成功（spec 7：重試最多 3 次）。
任一項不符以非 0 結束；結束時關閉行程、刪除暫時資料庫。崩潰用 Popen.kill() 硬砍（POSIX 為 SIGKILL）。

已知限制：「候選已存、工作狀態未更新」之間崩潰會重複建候選，見 #107（Dev-B），本腳本不涵蓋。

用法（在 backend/ 下）：
  .venv/bin/python ../scripts/drills/exception_drill.py              # macOS／Linux
  .venv\Scripts\python.exe ..\scripts\drills\exception_drill.py       # Windows
"""

import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

import httpx  # noqa: E402
from alembic import command  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.config import DEFAULT_ENV_FILE, load_env_file  # noqa: E402
from tests.conftest import alembic_config  # noqa: E402

DB = "g4_drill_ex"                  # 寫死，避免動到開發資料庫
PORT = 8765                         # 避開開發用的 8000
TOKEN = "drill-local-token"  # noqa: S105 只用於本機暫時資料庫的測試值，不是正式 token
API = f"http://127.0.0.1:{PORT}/api/v1"
SEED = BACKEND.parent / "scripts" / "e2e_seeds" / "weekly.sql"
EXTERNAL = "drill-external"         # 外部連線的 application_name，用來和服務端連線區分
CONNECTION_DROPPED = {"ReadError", "RemoteProtocolError"}   # 行程被砍時 httpx 的例外（依平台與時機而定）

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'✓' if ok else '✗'} {name}{'：' + detail if detail else ''}")


class Server:
    """以真實行程啟動後端（app.main.run：含背景工作與排程）；kill() 硬砍行程模擬崩潰。"""

    def __init__(self, db_url: str, log_dir: Path):
        self.db_url, self.log_dir, self.proc, self.n = db_url, log_dir, None, 0

    def start(self) -> None:
        self.n += 1
        env = dict(os.environ, G4_DATABASE_URL=self.db_url, G4_API_TOKEN=TOKEN, G4_PORT=str(PORT),
                   AI_PROVIDER="off", PYTHONUTF8="1")
        log = (self.log_dir / f"server-{self.n}.log").open("wb")
        self.proc = subprocess.Popen([sys.executable, "-c", "from app.main import run; run()"],  # noqa: S603
                                     env=env, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                if httpx.get(f"{API}/meta/health", headers=auth(), timeout=1).status_code == 200:
                    return
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        raise RuntimeError("後端沒有啟動")

    def kill(self) -> None:
        self.proc.kill()   # POSIX 為 SIGKILL、Windows 為 TerminateProcess：都不給行程收尾
        self.proc.wait(timeout=10)


def auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def api(method: str, path: str, **kw) -> httpx.Response:
    return httpx.request(method, f"{API}{path}", headers=auth(), timeout=30, **kw)


def in_background(fn):
    """在另一個執行緒送請求；回傳 (thread, box)，box 收結果或例外。"""
    box: dict = {}

    def run():
        try:
            box["response"] = fn()
        except Exception as exc:   # noqa: BLE001 行程被砍時連線會中斷，屬於預期
            box["error"] = type(exc).__name__
    t = threading.Thread(target=run)
    t.start()
    return t, box


def wait_for_lock_wait(engine, pattern: str, timeout: float = 10.0) -> dict | None:
    """等到服務端有一條連線卡在鎖等待，且其查詢含 pattern；回傳該列（含 backend_xid）。"""
    sql = text("SELECT pid, backend_xid::text AS xid, query FROM pg_stat_activity "
               "WHERE datname = :db AND application_name <> :ext AND wait_event_type = 'Lock' AND query ILIKE :p")
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        with engine.connect() as c:
            row = c.execute(sql, {"db": DB, "ext": EXTERNAL, "p": f"%{pattern}%"}).mappings().first()
        if row:
            return dict(row)
        time.sleep(0.05)
    return None


def scalar(engine, sql: str, **params):
    with engine.connect() as c:
        return c.execute(text(sql), params).scalar_one()


def task_state(engine, ids: list[int]) -> list[tuple]:
    with engine.connect() as c:
        return [tuple(r) for r in c.execute(text(
            "SELECT id, latest_due, version FROM tasks WHERE id = ANY(:ids) ORDER BY id"), {"ids": ids})]


def versions(engine, ids: list[int]) -> dict[int, int]:
    return {i: v for i, _, v in task_state(engine, ids)}


def external(db_url: str):
    """外部連線（模擬另一個行程或維運操作），autocommit 關閉、手動控制交易。"""
    eng = create_engine(db_url, connect_args={"application_name": EXTERNAL})
    return eng, eng.connect()


def scenario_a(server: Server, engine, db_url: str) -> None:
    print("A 重啟時有 running 工作")
    lines = "\n".join(f"[10:{i:02d}] 阿德：第 {i + 1} 項進度正常" for i in range(31))   # 超過 30 行 → 背景工作
    ext_eng, ext = external(db_url)
    ext.execute(text("LOCK TABLE ai_runs IN EXCLUSIVE MODE"))   # 工作寫 ai_runs 時會卡住，停在 running
    job_id = api("POST", "/ingest", json={"text": lines, "project_id": 1}).json()["job_id"]
    stuck = wait_for_lock_wait(engine, "ai_runs")
    status, attempts = scalar(engine, "SELECT status FROM jobs WHERE id = :i", i=job_id), \
        scalar(engine, "SELECT attempts FROM jobs WHERE id = :i", i=job_id)
    check("A1 工作處理中被鎖住", stuck is not None and status == "running", f"status={status}、attempts={attempts}")
    server.kill()
    ext.rollback()
    ext.close()
    ext_eng.dispose()
    check("A2 崩潰後工作停在 running", scalar(engine, "SELECT status FROM jobs WHERE id = :i", i=job_id) == "running")
    server.start()
    end = time.monotonic() + 15
    while time.monotonic() < end:
        job = api("GET", f"/ingest/jobs/{job_id}").json()
        if job["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.2)
    check("A3 重啟後續跑完成（AI 關閉 → failed 並附手動建立提示）",
          job["status"] == "failed" and "手動建立" in (job["error"] or ""), f"status={job['status']}")
    check("A4 attempts 保留後再加一次", job["attempts"] == attempts + 1, f"{attempts} → {job['attempts']}")


def scenario_b(server: Server, engine, db_url: str) -> None:
    print("B 寫入中途崩潰（AC-57）")
    ids = [13, 14, 22]
    before = task_state(engine, ids)
    events0, batches0 = scalar(engine, "SELECT count(*) FROM events"), scalar(engine, "SELECT count(*) FROM batches")
    body = {"items": [{"task_id": i, "expected_version": v} for i, v in versions(engine, ids).items()],
            "days": 3, "reason": "underestimated", "mark": "none"}
    ext_eng, ext = external(db_url)
    ext.execute(text("LOCK TABLE events IN EXCLUSIVE MODE"))   # commit 寫完 batch、寫第一筆事件時卡住
    t, box = in_background(lambda: api("POST", "/projects/1/bulk-shift/commit", json=body))
    stuck = wait_for_lock_wait(engine, "events")
    check("B1 交易已寫入、卡在寫事件", stuck is not None and stuck["xid"] is not None,
          f"backend_xid={stuck and stuck['xid']}")
    server.kill()
    t.join(timeout=10)
    ext.rollback()
    ext.close()
    ext_eng.dispose()
    check("B2 請求因行程崩潰而連線中斷", not t.is_alive() and box.get("error") in CONNECTION_DROPPED,
          box.get("error", "（沒有例外）"))
    check("B3 任務的日期與版本都沒變", task_state(engine, ids) == before)
    check("B4 events、batches 筆數沒變",
          (scalar(engine, "SELECT count(*) FROM events"), scalar(engine, "SELECT count(*) FROM batches"))
          == (events0, batches0))
    server.start()
    r = api("POST", "/projects/1/bulk-shift/commit", json=body)
    check("B5 重啟後同一請求正常完成", r.status_code == 200 and r.json()["updated"] == 3, f"HTTP {r.status_code}")


def scenario_c(engine, db_url: str) -> None:
    print("C 資料庫鎖定")
    # C1：鎖住後放開，不改資料
    v = versions(engine, [22])[22]
    events0 = scalar(engine, "SELECT count(*) FROM events WHERE task_id = 22")
    ext_eng, ext = external(db_url)
    ext.execute(text("SELECT id FROM tasks WHERE id = 22 FOR UPDATE"))
    started = time.monotonic()
    t, box = in_background(lambda: api("POST", "/tasks/22/adjust-due", json={
        "expected_version": v, "new_due": "2026-12-01", "reason": "underestimated", "mark": "none"}))
    waiting = wait_for_lock_wait(engine, "tasks") is not None
    time.sleep(2)
    ext.rollback()
    t.join(timeout=15)
    r, elapsed = box.get("response"), time.monotonic() - started
    check("C1 鎖住時請求等待，放開後完成、只寫一筆事件",
          waiting and r is not None and r.status_code == 200 and elapsed >= 2
          and scalar(engine, "SELECT count(*) FROM events WHERE task_id = 22") == events0 + 1,
          f"HTTP {r and r.status_code}、等待 {elapsed:.1f} 秒")

    # C2：鎖住期間對方改了版本
    v = versions(engine, [14])[14]
    due0 = task_state(engine, [14])[0][1]
    events0 = scalar(engine, "SELECT count(*) FROM events WHERE task_id = 14")
    ext.execute(text("SELECT id FROM tasks WHERE id = 14 FOR UPDATE"))
    t, box = in_background(lambda: api("POST", "/tasks/14/adjust-due", json={
        "expected_version": v, "new_due": "2026-12-02", "reason": "underestimated"}))
    wait_for_lock_wait(engine, "tasks")
    ext.execute(text("UPDATE tasks SET version = version + 1 WHERE id = 14"))
    ext.commit()
    t.join(timeout=15)
    r = box.get("response")
    code = r.json().get("error", {}).get("code") if r is not None else None
    check("C2 對方改了版本 → STALE_VERSION、不寫入",
          r is not None and r.status_code == 409 and code == "STALE_VERSION"
          and task_state(engine, [14])[0][1] == due0
          and scalar(engine, "SELECT count(*) FROM events WHERE task_id = 14") == events0,
          f"HTTP {r and r.status_code} {code}")

    # C3：死結。外部先鎖 22；服務端整批順延依 id 鎖 13、14 後等 22；外部再鎖 13 → 死結。
    # 外部把 deadlock_timeout 調長，讓服務端先偵測、被選為犧牲者（40P01）；服務端應整筆重試並成功。
    ids = [13, 14, 22]
    body = {"items": [{"task_id": i, "expected_version": v} for i, v in versions(engine, ids).items()],
            "days": 1, "reason": "underestimated", "mark": "none"}
    deadlocks0 = scalar(engine, "SELECT deadlocks FROM pg_stat_database WHERE datname = :d", d=DB)
    ext.execute(text("SET deadlock_timeout = '10s'"))
    ext.execute(text("SELECT id FROM tasks WHERE id = 22 FOR UPDATE"))
    t, box = in_background(lambda: api("POST", "/projects/1/bulk-shift/commit", json=body))
    wait_for_lock_wait(engine, "tasks")
    ext_error = None
    try:
        ext.execute(text("SELECT id FROM tasks WHERE id = 13 FOR UPDATE"))   # 服務端被犧牲後才拿得到
    except Exception as exc:   # noqa: BLE001 若外部反而被選為犧牲者，記下來判為不符
        ext_error = type(exc).__name__
    ext.rollback()
    t.join(timeout=20)
    r = box.get("response")
    time.sleep(0.5)   # pg_stat_database 的計數有延遲
    deadlocks = scalar(engine, "SELECT deadlocks FROM pg_stat_database WHERE datname = :d", d=DB)
    check("C3 發生死結、服務端為犧牲者，整筆重試後成功",
          ext_error is None and deadlocks > deadlocks0 and r is not None and r.status_code == 200
          and r.json()["updated"] == 3,
          f"deadlocks {deadlocks0}→{deadlocks}、外部連線錯誤={ext_error}、HTTP {r and r.status_code}")
    ext.close()
    ext_eng.dispose()


def main() -> int:
    load_env_file(Path(DEFAULT_ENV_FILE))
    admin = make_url(os.environ["G4_TEST_ADMIN_URL"])
    db_url = admin.set(database=DB).render_as_string(hide_password=False)
    admin_eng = create_engine(admin, isolation_level="AUTOCOMMIT")
    with admin_eng.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{DB}" WITH (FORCE)'))
        c.execute(text(f'CREATE DATABASE "{DB}"'))
    command.upgrade(alembic_config(db_url), "head")
    engine = create_engine(db_url)
    with engine.begin() as c:
        c.connection.driver_connection.cursor().execute(SEED.read_text(encoding="utf-8"))
    log_dir = Path(tempfile.mkdtemp(prefix="g4-drill-"))
    server = Server(db_url, log_dir)
    try:
        server.start()
        api("POST", "/settings/onboarding/complete", json={"skipped": True})
        scenario_a(server, engine, db_url)
        scenario_b(server, engine, db_url)
        scenario_c(engine, db_url)
    finally:
        if server.proc and server.proc.poll() is None:
            server.proc.terminate()
            server.proc.wait(timeout=10)
        engine.dispose()
        with admin_eng.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{DB}" WITH (FORCE)'))
        admin_eng.dispose()
    failed = [n for n, ok, _ in results if not ok]
    print(f"{len(results) - len(failed)}/{len(results)} 項通過；行程日誌在 {log_dir}；暫時資料庫已刪除。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
