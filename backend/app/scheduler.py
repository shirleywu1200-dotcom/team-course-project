"""原文到期清除排程（todo 8.5、FR-GOV-01；Phase 8 SDD Q5）。

與 API 同一個行程的背景執行緒：啟動時先跑一次，之後每小時一次。清除是冪等的，漏跑一輪下一輪會補上。
測試直接呼叫 `run_once`。
"""

import logging
import threading
import time

from app.db.database import Database
from app.domain import governance

log = logging.getLogger(__name__)
PURGE_INTERVAL_S = 3600


def run_once(db: Database) -> int:
    purged = db.run(governance.purge_expired)
    log.info("到期原文清除 %s 筆", purged)
    return purged


def _loop(db: Database) -> None:
    while True:
        try:
            run_once(db)
        except Exception as exc:   # 單輪失敗不讓執行緒結束，下一輪再試
            log.error("清除排程例外：%s", type(exc).__name__)
        time.sleep(PURGE_INTERVAL_S)


def start(db: Database) -> threading.Thread:
    thread = threading.Thread(target=_loop, args=(db,), name="purge-scheduler", daemon=True)
    thread.start()
    return thread
