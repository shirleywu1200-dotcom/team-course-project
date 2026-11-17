"""週報（spec 5.14；todo Phase 10）。"""

from datetime import date

from fastapi import APIRouter, Depends, Path, Query

from app.ai.client import AIClient
from app.api.deps import get_ai, get_db
from app.api.responses import WeeklyReportOut
from app.api.schemas import ManualText, WeeklyDraft
from app.db.database import Database
from app.domain import weekly_service

router = APIRouter(prefix="/reports/weekly", tags=["reports"])

ReportId = Path(ge=1, le=2**63 - 1)


@router.post("/draft", response_model=WeeklyReportOut)
def draft(body: WeeklyDraft, db: Database = Depends(get_db), ai: AIClient = Depends(get_ai)):
    return weekly_service.generate(db, ai, body.week_start)


@router.get("", response_model=WeeklyReportOut,
            responses={404: {"description": "該週尚未產生（正常狀態，不是錯誤；spec 5.14）"}})
def get_by_week(week_start: date = Query(), db: Database = Depends(get_db)):
    return weekly_service.get_by_week(db, week_start)


@router.get("/{report_id}", response_model=WeeklyReportOut)
def get_report(report_id: int = ReportId, db: Database = Depends(get_db)):
    return weekly_service.get(db, report_id)


@router.put("/{report_id}/manual", response_model=WeeklyReportOut)
def save_manual(body: ManualText, report_id: int = ReportId, db: Database = Depends(get_db)):
    return weekly_service.save_manual(db, report_id, body.manual_text)
