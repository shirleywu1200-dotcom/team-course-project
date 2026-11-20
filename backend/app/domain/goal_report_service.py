"""目標回報的產生、讀取與人工版（todo 9.10；spec 5.13「目標回報」、5.3a〈AI-04〉；FR-GOL-06、07）。

流程比照週報（weekly_service）：讀資料（一個交易）→ 在交易外呼叫 AI-04 → 存檔（一個交易）。
每次 AI 嘗試各寫一列 ai_runs，不存 raw_output（5.3a）。三個端點輸出相同；validated 一律拿存下的草稿與
figures 對目前的資料重跑 R3（第 5 點），所以之後關聯、標題、回報變了，對不上就改回統計表。
"""

import logging
import time

from sqlalchemy import Connection

from app.ai.client import DEFAULT_TIMEOUT_S, AIClient, AIUnavailable
from app.clock import get_clock
from app.db.database import Database
from app.db.repo import ai_runs_repo, goal_reports_repo
from app.domain import ai04, ai05, goal_report
from app.domain.text import check_manual_text

log = logging.getLogger("g4")

MAX_ATTEMPTS = 3   # 同 AI-05：任何失敗都算一次、最多 3 次；AI 不可用與 R3 失敗立刻停


def _attempt(ai: AIClient, payload: dict) -> tuple[str, str | None, tuple | None, bool]:
    """呼叫一次 AI-04。回傳 (ai_runs.status, error, (draft, figures) 或 None, 是否立刻停)。"""
    try:
        draft, figures = ai04.parse_output(ai.call(ai04.NODE, payload, timeout_s=DEFAULT_TIMEOUT_S))
    except Exception as exc:   # noqa: BLE001 供應商可能丟出任何例外；AI 失敗一律走退路（spec 5.3）
        return ai_runs_repo.status_for(exc), type(exc).__name__, None, isinstance(exc, AIUnavailable)
    if not ai04.reconcile(draft, figures, payload):   # R3 不符：記成格式不合，不重試（5.3a）
        return "invalid_output", "R3_MISMATCH", None, True
    return "ok", None, (draft, figures), False


def _ask_ai(db: Database, ai: AIClient, payload: dict) -> tuple[str, tuple | None]:
    """回傳 (ai_status, (draft, figures) 或 None)。最終狀態以最後一次嘗試為準；log、error 只記類別或錯誤碼。"""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        status, error, result, stop = _attempt(ai, payload)
        run = {"node_id": ai04.NODE, "status": status, "attempt": attempt, "error": error,
               "latency_ms": int((time.monotonic() - started) * 1000), "created_at": get_clock().now()}
        db.run(lambda c, r=run: ai_runs_repo.insert_run(c, r))
        if result is not None:
            return "ok", result
        if stop:
            break
    log.warning("AI-04 失敗：%s", error)
    return ("invalid_output" if status == "invalid_output" else "unavailable"), None


def _validated(row: dict, current: goal_report.ReportInput) -> bool:
    """存下的成功草稿對目前資料重跑 R3；沒有成功草稿（失敗或人工版建的列）一律 False。"""
    if row["ai_status"] != "ok" or row["ai_draft"] is None or row["ai_items"] is None:
        return False
    figures = [(f["key"], f["value"]) for f in row["ai_items"]]
    return ai04.reconcile(row["ai_draft"], figures, current.payload)


def _view(row: dict, validated: bool, *, ai_status: str | None = None, excluded_private: int | None = None) -> dict:
    """輸出（spec 5.13 第 3 點）。ai_status、excluded_private 有給時是這次產生失敗的值，其餘取存下的列。"""
    return {
        "id": row["id"], "goal_id": row["goal_id"],
        "ai_status": row["ai_status"] if ai_status is None else ai_status,
        "excluded_private": row["excluded_private"] if excluded_private is None else excluded_private,
        "draft": row["ai_draft"] if validated else None, "validated": validated,
        "manual_text": row["manual_text"], "updated_at": row["updated_at"],
    }


def generate(db: Database, ai: AIClient, goal_id: int) -> dict:
    data = db.run(lambda c: goal_report.collect(c, goal_id))   # 目標不存在：NOT_FOUND
    # linked=0 或綁私人專案的目標：依規則刻意不呼叫，不寫 ai_runs（5.3；第 4、7 點）
    status, result = _ask_ai(db, ai, data.payload) if data.sendable else ("unavailable", None)

    def store(conn: Connection) -> dict:
        now = get_clock().now()
        if result is not None:
            draft, figures = result
            goal_reports_repo.save_success(conn, goal_id, draft, [{"key": k, "value": v} for k, v in figures],
                                           data.excluded_private, now)
            row = goal_reports_repo.get(conn, goal_id)
            return _view(row, _validated(row, goal_report.collect(conn, goal_id)))
        goal_reports_repo.save_failure(conn, goal_id, status, data.excluded_private, now)
        # 失敗時回這次的退路，即使存著上一次成功的初稿（比照週報 #18 H2）
        return _view(goal_reports_repo.get(conn, goal_id), False, ai_status=status,
                     excluded_private=data.excluded_private)

    return db.run(store)


def get(db: Database, goal_id: int) -> dict:
    """不呼叫 AI、不寫入（第 2 點）。"""
    def read(conn: Connection) -> dict:
        current = goal_report.collect(conn, goal_id)   # 目標不存在：NOT_FOUND
        row = goal_reports_repo.get(conn, goal_id)     # 尚未產生：NOT_FOUND（details 只有 goal_id）
        return _view(row, _validated(row, current))
    return db.run(read)


def save_manual(db: Database, goal_id: int, manual_text: str | None) -> dict:
    check_manual_text(manual_text, ai05.TEXT_MAX_CHARS)   # 上限同週報人工版（第 6 點）

    def write(conn: Connection) -> dict:
        current = goal_report.collect(conn, goal_id)
        goal_reports_repo.save_manual(conn, goal_id, manual_text, get_clock().now())
        row = goal_reports_repo.get(conn, goal_id)
        return _view(row, _validated(row, current))
    return db.run(write)
