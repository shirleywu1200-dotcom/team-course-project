"""收件背景工作（todo 7.5、FR-INB-05、08）。

與 API 同一個行程的背景執行緒：每次取一筆 queued 工作處理。測試直接呼叫 `run_once`。
"""

import logging
import threading
import time

from app.ai.client import AIClient
from app.clock import get_clock
from app.db.database import Database
from app.db.repo import jobs_repo
from app.domain.inbox.ingest import FAILED_MESSAGE, process_sources, result_summary

log = logging.getLogger(__name__)
IDLE_SLEEP_S = 1.0
JOB_TIMEOUT_S = 60.0   # 整份貼上一次送 AI-01；150 則實測 25.8 秒，超過同步的 20 秒（13-4-sdd 4.3）


def run_once(db: Database, ai: AIClient) -> int | None:
    """處理一筆工作，回傳工作 id；沒有工作時回 None。"""
    job = db.run(lambda c: jobs_repo.claim_next(c, get_clock().now()))
    if job is None:
        return None
    p = job["payload"]
    try:
        outcome = process_sources(db, ai, p["source_ids"], p["project_id"], job_id=job["id"],
                                  attempts_done=job["attempts"], timeout_s=JOB_TIMEOUT_S)
    except Exception:   # 不讓工作卡在 running；前端輪詢才看得到 failed 與手動建立的提示
        db.run(lambda c: jobs_repo.update(c, job["id"], {"status": "failed", "error": FAILED_MESSAGE,
                                                          "updated_at": get_clock().now()}))
        raise
    ok = outcome.ai_status == "ok"
    fields = {"status": "succeeded" if ok else "failed", "updated_at": get_clock().now(),
              "result": result_summary(outcome, p["duplicates"], p["unparsed_lines"])
              | {"ai_status": outcome.ai_status, "candidate_ids": outcome.candidate_ids},
              "error": None if ok else outcome.message}
    db.run(lambda c: jobs_repo.update(c, job["id"], fields))
    return job["id"]


def reset_running(db: Database) -> int:
    return db.run(lambda c: jobs_repo.reset_running(c, get_clock().now()))


def _loop(db: Database, ai: AIClient) -> None:
    while True:
        try:
            if run_once(db, ai) is None:
                time.sleep(IDLE_SLEEP_S)
        except Exception as exc:   # 單筆失敗不讓執行緒結束；工作留在 running，重啟時重設
            log.error("worker 例外：%s", type(exc).__name__)
            time.sleep(IDLE_SLEEP_S)


def start(db: Database, ai: AIClient) -> threading.Thread:
    """服務啟動時呼叫：先把 running 重設為 queued，再啟動背景執行緒。"""
    reset_running(db)
    thread = threading.Thread(target=_loop, args=(db, ai), name="ingest-worker", daemon=True)
    thread.start()
    return thread
