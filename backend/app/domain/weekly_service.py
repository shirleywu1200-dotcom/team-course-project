"""週報的產生、讀取與人工版（todo 10.2、10.4；spec 5.14）。

流程：彙整（一個交易）→ 在交易外呼叫 AI-05 → 存檔（一個交易）。AI 呼叫期間不持有資料庫連線。
三個端點的輸出相同；GET 用存下的 ai_items 對目前的歷程重新對帳（#18 第 1 點 (b)）。
AI-05 的 ai_runs 紀錄（FR-AI-02）等 PR #20 合併後沿用 Dev-B 的 ai_runs_repo 補上（Phase 10 第三段）。
"""

import logging
from datetime import date, timedelta

from sqlalchemy import Connection

from app.ai.client import AIClient, AIInvalidOutput
from app.clock import get_clock
from app.db.database import Database
from app.db.repo import reports_repo, weekly_repo
from app.domain import ai05, weekly_report
from app.domain.due import check_date_range
from app.errors import DomainError

log = logging.getLogger("g4")

MANUAL_MAX_CHARS = 20_000


def check_week_start(week_start: date, today: date) -> None:
    """週一（第 5 點）、不晚於本週（G7）、不早於今天前 365 天（J6）。"""
    weekly_report.check_monday(week_start)
    if week_start > today - timedelta(days=today.weekday()):
        raise DomainError("VALIDATION_ERROR", "week_start 不能晚於本週", {"fields": ["week_start"]})
    check_date_range(week_start, today)


def _ask_ai(ai: AIClient, data: weekly_report.WeekData) -> tuple[str, str | None, list[dict] | None]:
    """回傳 (ai_status, draft, items)。逾時與其他錯誤一律算 unavailable（#18 J3）；log 只記類別。"""
    try:
        draft, items = ai05.parse_output(ai.call(ai05.NODE, ai05.build_payload(data)))
    except AIInvalidOutput:
        return "invalid_output", None, None
    except Exception as exc:   # noqa: BLE001 供應商可能丟出任何例外；AI 失敗一律走退路（spec 5.3）
        log.warning("AI-05 失敗：%s", type(exc).__name__)
        return "unavailable", None, None
    if not weekly_report.reconcile(items, data):   # R4 對不上也算失敗（#18 J2）
        return "invalid_output", None, None
    return "ok", draft, items


def _view(conn: Connection, row: dict) -> dict:
    """依目前的歷程組出回應：validated 由存下的 ai_items 重新對帳。"""
    data = weekly_report.collect(conn, row["period_start"])
    valid = False
    if row["ai_status"] == "ok" and row["ai_items"] is not None:
        next_ids = [i["task_id"] for i in row["ai_items"] if i["section"] == "next"]
        valid = weekly_report.reconcile(row["ai_items"], data,
                                        next_allowed=weekly_repo.work_task_ids(conn, next_ids))
    return {
        "id": row["id"], "week_start": row["period_start"], "ai_status": row["ai_status"],
        "excluded_private": row["excluded_private"],
        "draft": row["ai_draft"] if valid else None,
        "items": row["ai_items"] if valid else weekly_report.fallback_items(data),
        "validated": valid, "manual_text": row["manual_text"], "updated_at": row["updated_at"],
    }


def generate(db: Database, ai: AIClient, week_start: date) -> dict:
    check_week_start(week_start, get_clock().today())
    data = db.run(lambda c: weekly_report.collect(c, week_start))
    status, draft, items = _ask_ai(ai, data)

    def store(conn: Connection) -> dict:
        now = get_clock().now()
        if status == "ok":
            rid = reports_repo.save_success(conn, week_start, draft, items, data.excluded_private, now)
            return _view(conn, reports_repo.get_weekly(conn, rid))
        row = reports_repo.get_weekly(conn, reports_repo.save_failure(conn, week_start, status,
                                                                       data.excluded_private, now))
        # 這次失敗：回應一律是這次彙整的退路內容，即使存著上一次成功的初稿（#18 H2）
        return {"id": row["id"], "week_start": week_start, "ai_status": status,
                "excluded_private": data.excluded_private, "draft": None,
                "items": weekly_report.fallback_items(data), "validated": False,
                "manual_text": row["manual_text"], "updated_at": row["updated_at"]}

    return db.run(store)


def get(db: Database, report_id: int) -> dict:
    return db.run(lambda c: _view(c, reports_repo.get_weekly(c, report_id)))


def save_manual(db: Database, report_id: int, manual_text: str | None) -> dict:
    if manual_text is not None:
        if len(manual_text) > MANUAL_MAX_CHARS:
            raise DomainError("PAYLOAD_TOO_LARGE", details={"max_chars": MANUAL_MAX_CHARS})
        if "\x00" in manual_text:   # PostgreSQL 的文字欄位不收 NUL
            raise DomainError("VALIDATION_ERROR", "manual_text 含有不能使用的字元", {"fields": ["manual_text"]})

    def run(conn: Connection) -> dict:
        reports_repo.save_manual(conn, report_id, manual_text, get_clock().now())
        return _view(conn, reports_repo.get_weekly(conn, report_id))

    return db.run(run)
