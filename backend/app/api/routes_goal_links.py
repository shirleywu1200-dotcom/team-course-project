"""目標關聯端點（spec 5.13；todo 9.6、9.7；#47 G1、G3）。"""

from fastapi import APIRouter, Depends

from app.ai.client import AIClient
from app.api.deps import get_ai, get_db
from app.api.responses import GoalSuggestOut, PendingLinkOut, TaskEventOut
from app.api.schemas import GoalLinkIn
from app.api.serialize import event_out, pending_link_out, task_out
from app.db.database import Database
from app.domain import goal_links, goal_suggest

router = APIRouter(prefix="/goal-links", tags=["goals"])


@router.get("/pending", response_model=PendingLinkOut)
def pending_links(db: Database = Depends(get_db)):
    items = [pending_link_out(r) for r in db.run(goal_links.pending)]
    return {"items": items, "total": len(items)}


@router.post("/suggest", response_model=GoalSuggestOut)
def suggest_links(db: Database = Depends(get_db), ai: AIClient = Depends(get_ai)):
    """AI-03 建議；AI 失敗也回 200 加退路（AC-50）。不帶 body。"""
    return goal_suggest.suggest(db, ai)


@router.post("", response_model=TaskEventOut,
             responses={404: {"description": "任務不存在（NOT_FOUND）"},
                        409: {"description": "版本不符（STALE_VERSION）"},
                        422: {"description": "任務未完成或沒有回報、目標不存在或已封存、"
                                             "ai_run_id 不是可用的 AI-03 紀錄（VALIDATION_ERROR）；"
                                             "與目前關聯相同（NO_CHANGE）"}})
def link_goal(body: GoalLinkIn, db: Database = Depends(get_db)):
    task, event = db.run(lambda c: goal_links.link(c, body.task_id, body.goal_id, body.expected_version,
                                                        body.ai_run_id))
    return {"task": task_out(task), "event": event_out(event)}
