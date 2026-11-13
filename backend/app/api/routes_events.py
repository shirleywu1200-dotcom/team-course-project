"""註記、時間管理統計、原因選項、健康檢查（spec 5.8、5.15）。

`GET /events` 歷程查詢屬 Phase 5（Dev-B），不在此實作。
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from app.ai.client import AIClient
from app.api.deps import get_ai, get_db
from app.api.schemas import Annotation
from app.api.serialize import event_out
from app.db.database import Database
from app.domain import marks
from app.domain.reasons import BASELINE_REASONS, BASELINE_TYPES, DUE_REASONS

router = APIRouter(tags=["events"])


@router.post("/events/{event_id}/annotations", status_code=201)
def annotate(event_id: int, body: Annotation, db: Database = Depends(get_db)):
    event, effective = db.run(lambda c: marks.annotate(c, event_id, body.mark, body.reason, body.note))
    return {"event": event_out(event), "effective_mark": effective}


@router.get("/stats/time-management")
def time_management(from_: date | None = Query(None, alias="from"), to: date | None = None,
                    db: Database = Depends(get_db)):
    return db.run(lambda c: marks.time_mgmt_stats(c, from_, to))


@router.get("/meta/reasons")
def reasons():
    return {
        "due": DUE_REASONS,
        "baseline_types": [{"code": k, "label": v} for k, v in BASELINE_TYPES.items()],
        "baseline_reasons": [{"code": k, "label": v} for k, v in BASELINE_REASONS.items()],
    }


@router.get("/meta/health")
def health(db: Database = Depends(get_db), ai: AIClient = Depends(get_ai)):
    try:
        db.run(lambda c: c.execute(text("SELECT 1")).scalar_one())
        db_status = "ok"
    except Exception:  # noqa: BLE001 健康檢查只回報狀態
        db_status = "error"
    return {"db": db_status, "ai": "ok" if ai.health() else "unavailable"}
