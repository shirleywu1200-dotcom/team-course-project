"""完成回報（FR-FBK-02～07、spec 5.12、6.5）。

星數與精力只來自使用者送的值，AI 不估、不代填（FR-FBK-07、FR-AI-06）；逾期天數由伺服器計算（FR-FBK-03）。
"""

from datetime import date

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import feedback_repo, rubrics_repo
from app.db.repo.tasks_repo import TaskRepo
from app.domain.events import is_mine, write_event
from app.errors import DomainError


def overdue_days(done_date: date, orig_due: date) -> int:
    """以原訂日為基準（FR-FBK-03）。"""
    return max(0, (done_date - orig_due).days)


def save(conn: Connection, task_id: int, *, actual_stars: int, energy: str, invest_vs_expected: str | None,
         rubric_id: int) -> tuple[dict, dict]:
    """同一交易寫入回報與一筆 feedback 事件；回傳 (回報, 事件)。"""
    task = TaskRepo(conn).get(task_id)
    if task["status"] != "done":
        raise DomainError("VALIDATION_ERROR", "只有已完成的任務可以填完成回報", {"fields": ["task_id"]})
    if not rubrics_repo.exists(conn, rubric_id):
        raise DomainError("VALIDATION_ERROR", "量表版本不存在", {"fields": ["rubric_id"]})
    values = {"actual_stars": actual_stars, "energy": energy, "invest_vs_expected": invest_vs_expected,
              "overdue_days": overdue_days(task["done_date"], task["orig_due"]), "rubric_id": rubric_id}
    saved = feedback_repo.insert_if_absent(conn, {"task_id": task_id, "created_at": get_clock().now()} | values)
    if saved is None:
        raise DomainError("FEEDBACK_EXISTS", details={"task_id": task_id})
    event = write_event(conn, task_id=task_id, task_title=task["title"], mine=is_mine(task),
                        project_id=task["project_id"], kind="feedback", field="completion_feedback",
                        from_value=None, to_value=str(saved["id"]), origin="manual", extra=values)
    return saved, event


def get(conn: Connection, task_id: int) -> dict:
    TaskRepo(conn).get(task_id)   # 任務不存在：NOT_FOUND
    saved = feedback_repo.get_by_task(conn, task_id)
    if saved is None:
        raise DomainError("NOT_FOUND", details={"task_id": task_id})
    return saved


def pending(conn: Connection) -> list[dict]:
    """待補完成回報（FR-FBK-05）；逾期天數與儲存時的算法相同。"""
    return [row | {"overdue_days": overdue_days(row["done_date"], row["orig_due"])}
            for row in feedback_repo.pending_tasks(conn)]
