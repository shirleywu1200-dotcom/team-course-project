"""完成回報端點（spec 5.12；todo 9.1、9.2）。"""

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.api.responses import FeedbackOut, FeedbackSaveOut, PendingFeedbackOut
from app.api.schemas import FeedbackSave
from app.api.serialize import event_out
from app.db.database import Database
from app.domain import feedback

router = APIRouter(tags=["feedback"])

FEEDBACK_KEYS = ("id", "task_id", "actual_stars", "energy", "invest_vs_expected", "overdue_days", "rubric_id",
                 "created_at")
PENDING_KEYS = ("task_id", "title", "project_id", "done_date", "orig_due", "overdue_days", "expected_stars",
                "star_source")


def _feedback_out(row: dict) -> dict:
    return {k: row[k] for k in FEEDBACK_KEYS}


def _pending_out(row: dict) -> dict:
    return {k: row[k] for k in PENDING_KEYS} | {"owner": row["owner_name"]}


@router.put("/tasks/{task_id}/feedback", status_code=201, response_model=FeedbackSaveOut)
def save_feedback(task_id: int, body: FeedbackSave, db: Database = Depends(get_db)):
    saved, event = db.run(lambda c: feedback.save(c, task_id, actual_stars=body.actual_stars, energy=body.energy,
                                                  invest_vs_expected=body.invest_vs_expected,
                                                  rubric_id=body.rubric_id))
    return {"feedback": _feedback_out(saved), "event": event_out(event)}


@router.get("/tasks/{task_id}/feedback", response_model=FeedbackOut)
def get_feedback(task_id: int, db: Database = Depends(get_db)):
    return _feedback_out(db.run(lambda c: feedback.get(c, task_id)))


@router.get("/feedback/pending", response_model=PendingFeedbackOut)
def pending_feedback(db: Database = Depends(get_db)):
    items = [_pending_out(r) for r in db.run(feedback.pending)]
    return {"items": items, "total": len(items)}
