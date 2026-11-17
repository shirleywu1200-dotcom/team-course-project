"""歷程查詢與甘特資料端點（spec 5.5、5.8；todo Phase 5，Dev-B）。只讀。"""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_db
from app.api.responses import GanttOut, HistoryListOut
from app.api.serialize import event_out
from app.db.database import Database
from app.domain import history

router = APIRouter(tags=["history"])

EventKind = Literal["due", "annotation", "status", "task", "feedback", "goal", "baseline", "project"]


def _history_item(r: dict) -> dict:
    return event_out(r) | {"project_name": r["project_name"], "effective_mark": r["effective_mark"],
                           "source": r["source"]}


def _list(db: Database, filters: dict, limit: int, offset: int) -> dict:
    rows, total = db.run(lambda c: history.list_events(c, filters, limit, offset))
    return {"items": [_history_item(r) for r in rows], "total": total}


@router.get("/events", response_model=HistoryListOut)
def list_events(project_id: str | None = Query(None, pattern=r"^(none|\d+)$"), kind: EventKind | None = None,
                task_id: int | None = None, batch_id: int | None = None,
                from_: date | None = Query(None, alias="from"), to: date | None = None,
                limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                db: Database = Depends(get_db)):
    pid = project_id if project_id in (None, "none") else int(project_id)
    filters = {"project_id": pid, "kind": kind, "task_id": task_id, "batch_id": batch_id,
               "date_from": from_, "date_to": to}
    return _list(db, filters, limit, offset)


@router.get("/projects/{project_id}/history", response_model=HistoryListOut)
def project_history(project_id: int, kind: EventKind | None = None, task_id: int | None = None,
                    batch_id: int | None = None, from_: date | None = Query(None, alias="from"),
                    to: date | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                    db: Database = Depends(get_db)):
    filters = {"project_id": project_id, "kind": kind, "task_id": task_id, "batch_id": batch_id,
               "date_from": from_, "date_to": to}
    return _list(db, filters, limit, offset)


@router.get("/projects/{project_id}/gantt", response_model=GanttOut)
def project_gantt(project_id: int, db: Database = Depends(get_db)):
    return db.run(lambda c: history.project_gantt(c, project_id))
