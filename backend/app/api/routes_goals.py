"""目標端點（spec 5.13；todo 9.5、9.8、9.9）。關聯在 routes_goal_links；/matrix 要排在 /{goal_id} 之前。"""

from fastapi import APIRouter, Depends

from app.ai.client import AIClient
from app.api.deps import get_ai, get_db
from app.api.responses import GoalListOut, GoalMatrixOut, GoalOut, GoalPatchOut, GoalReportOut, GoalStatsOut
from app.api.schemas import GoalCreate, GoalPatch, ManualText
from app.api.serialize import event_out, goal_out
from app.db.database import Database
from app.db.repo import goals_repo
from app.domain import goal_report_service, goal_stats, goals

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=GoalListOut)
def list_goals(include_archived: bool = False, db: Database = Depends(get_db)):
    return {"items": [goal_out(g) for g in db.run(lambda c: goals_repo.list_all(c, include_archived))]}


@router.post("", status_code=201, response_model=GoalOut)
def create_goal(body: GoalCreate, db: Database = Depends(get_db)):
    return goal_out(db.run(lambda c: goals.create_goal(c, **body.model_dump())))


@router.get("/matrix", response_model=GoalMatrixOut)
def goal_matrix(db: Database = Depends(get_db)):
    return {"items": db.run(goal_stats.matrix)}


@router.get("/{goal_id}/stats", response_model=GoalStatsOut,
            responses={404: {"description": "目標不存在（NOT_FOUND）"}})
def goal_stats_of(goal_id: int, db: Database = Depends(get_db)):
    return db.run(lambda c: goal_stats.stats(c, goal_id))


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(goal_id: int, db: Database = Depends(get_db)):
    return goal_out(db.run(lambda c: goals_repo.get(c, goal_id)))


@router.patch("/{goal_id}", response_model=GoalPatchOut)
def patch_goal(goal_id: int, body: GoalPatch, db: Database = Depends(get_db)):
    goal, events = db.run(lambda c: goals.update_goal(c, goal_id, body.model_dump(exclude_unset=True)))
    return {"goal": goal_out(goal), "changes": [event_out(e) for e in events]}


@router.post("/{goal_id}/archive", response_model=GoalOut)
def archive_goal(goal_id: int, db: Database = Depends(get_db)):
    return goal_out(db.run(lambda c: goals.archive_goal(c, goal_id)))


# ---------- 目標回報（9.10；spec 5.13「目標回報」、AI-04） ----------

@router.post("/{goal_id}/report/draft", response_model=GoalReportOut)
def report_draft(goal_id: int, db: Database = Depends(get_db), ai: AIClient = Depends(get_ai)):
    return goal_report_service.generate(db, ai, goal_id)


@router.get("/{goal_id}/report", response_model=GoalReportOut,
            responses={404: {"description": "目標不存在，或尚未產生（正常狀態，不是錯誤；spec 5.13 第 2 點）"}})
def report_get(goal_id: int, db: Database = Depends(get_db)):
    return goal_report_service.get(db, goal_id)


@router.put("/{goal_id}/report/manual", response_model=GoalReportOut)
def report_manual(body: ManualText, goal_id: int, db: Database = Depends(get_db)):
    return goal_report_service.save_manual(db, goal_id, body.manual_text)
