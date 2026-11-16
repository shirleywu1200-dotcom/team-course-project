"""資料庫連線與交易。

每個業務操作透過 `Database.run(fn)` 在一個交易內執行：成功就 commit，
丟出任何例外就整筆 rollback（spec 6.8、AC-57）。
遇到死結或序列化失敗（SQLSTATE 40P01、40001）時整筆重試，最多 3 次。
"""

import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy import Connection, create_engine
from sqlalchemy.exc import DBAPIError

T = TypeVar("T")
RETRY_SQLSTATES = {"40P01", "40001"}
MAX_RETRIES = 3
RETRY_SLEEP_S = 0.05


def make_engine(url: str):
    # hide_parameters：資料庫例外訊息不帶 SQL 參數值，避免任務標題、備註等使用者內容進入 log（CLAUDE.md 資安 3）
    return create_engine(
        url,
        connect_args={"options": "-c timezone=Asia/Taipei"},
        pool_pre_ping=True,
        hide_parameters=True,
    )


class Database:
    def __init__(self, url: str):
        self.engine = make_engine(url)

    def run(self, fn: Callable[[Connection], T]) -> T:
        for attempt in range(MAX_RETRIES + 1):
            try:
                with self.engine.begin() as conn:
                    return fn(conn)
            except DBAPIError as exc:
                sqlstate = getattr(exc.orig, "sqlstate", None)
                if sqlstate in RETRY_SQLSTATES and attempt < MAX_RETRIES:
                    time.sleep(RETRY_SLEEP_S)
                    continue
                raise
        raise RuntimeError("unreachable")

    def dispose(self) -> None:
        self.engine.dispose()
