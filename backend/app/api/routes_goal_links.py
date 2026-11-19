"""目標關聯端點（spec 5.13；todo 9.6；#47 G1、G3）。AI-03 建議（POST /goal-links/suggest）在第三片加入。"""

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.api.responses import PendingLinkOut, TaskEventOut
from app.api.schemas import GoalLinkIn
from app.api.serialize import event_out, pending_link_out, task_out
from app.db.database import Database
from app.domain import goal_links

router = APIRouter(prefix="/goal-links", tags=["goals"])


@router.get("/pending", response_model=PendingLinkOut)
def pending_links(db: Database = Depends(get_db)):
    items = [pending_link_out(r) for r in db.run(goal_links.pending)]
    return {"items": items, "total": len(items)}


@router.post("", response_model=TaskEventOut,
             responses={404: {"description": "任務不存在（NOT_FOUND）"},
                        409: {"description": "版本不符（STALE_VERSION）"},
                        422: {"description": "任務未完成或沒有回報、目標不存在或已封存（VALIDATION_ERROR）；"
                                             "與目前關聯相同（NO_CHANGE）"}})
def link_goal(body: GoalLinkIn, db: Database = Depends(get_db)):
    task, event = db.run(lambda c: goal_links.link(c, body.task_id, body.goal_id, body.expected_version))
    return {"task": task_out(task), "event": event_out(event)}
