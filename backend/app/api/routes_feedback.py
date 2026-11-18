"""完成回報端點（spec 5.12；todo 9.1、9.2）。"""

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.api.responses import FeedbackOut, FeedbackSaveOut, PendingFeedbackOut
from app.api.schemas import FeedbackSave
from app.api.serialize import event_out, feedback_out, pending_feedback_out
from app.db.database import Database
from app.domain import feedback

router = APIRouter(tags=["feedback"])

TASK_NOT_FOUND = {"description": "任務不存在（NOT_FOUND）"}


@router.put("/tasks/{task_id}/feedback", status_code=201, response_model=FeedbackSaveOut,
            responses={404: TASK_NOT_FOUND,
                       409: {"description": "任務已有完成回報（FEEDBACK_EXISTS；修改回報 9.3 未開放）"}})
def save_feedback(task_id: int, body: FeedbackSave, db: Database = Depends(get_db)):
    saved, event = db.run(lambda c: feedback.save(c, task_id, actual_stars=body.actual_stars, energy=body.energy,
                                                  invest_vs_expected=body.invest_vs_expected,
                                                  rubric_id=body.rubric_id))
    return {"feedback": feedback_out(saved), "event": event_out(event)}


@router.get("/tasks/{task_id}/feedback", response_model=FeedbackOut,
            responses={404: {"description": "任務存在時代表尚未填寫（正常狀態）；或任務不存在（NOT_FOUND）"}})
def get_feedback(task_id: int, db: Database = Depends(get_db)):
    return feedback_out(db.run(lambda c: feedback.get(c, task_id)))


@router.get("/feedback/pending", response_model=PendingFeedbackOut)
def pending_feedback(db: Database = Depends(get_db)):
    items = [pending_feedback_out(r) for r in db.run(feedback.pending)]
    return {"items": items, "total": len(items)}
