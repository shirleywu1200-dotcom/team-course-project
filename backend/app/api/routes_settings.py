"""設定與量表端點（spec 5.4；todo 8.1～8.4，Dev-B）。"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import ConfigDict, Field, StringConstraints, field_validator

from app.ai.client import AIClient
from app.api.deps import get_ai, get_db
from app.api.schemas import Scope, Strict
from app.db.database import Database
from app.domain import rubrics, settings

router = APIRouter(tags=["settings"])

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
GoalType = Literal["growth", "time", "expectation"]


class SettingsPatch(Strict):
    model_config = ConfigDict(extra="forbid")   # 未知欄位回 VALIDATION_ERROR（SDD 第 2 節）

    default_scope: Scope | None = None
    role: Literal["project_owner", "wbs_owner", "both"] | None = None
    report_audience: Literal["manager", "client", "none"] | None = None
    confirm_time: Literal["12:00", "18:00", "21:00"] | None = None
    confirm_cap_min: Literal[3, 5, 10] | None = None
    remind_default: Literal["morning", "eve_before", "none"] | None = None
    retention_days: Literal[30, 90, 180] | None = None
    energy_def_high: ShortText | None = None
    energy_def_mid: ShortText | None = None
    energy_def_low: ShortText | None = None
    goal_types_enabled: list[GoalType] | None = None

    @field_validator("goal_types_enabled")
    @classmethod
    def _unique(cls, v):
        if v is not None and len(set(v)) != len(v):
            raise ValueError("目標類型不可重複")
        return v


class OnboardingIn(Strict):
    skipped: bool = False


class InterviewIn(Strict):
    q1: ShortText
    q2: ShortText
    q3: ShortText


class InterviewRecord(InterviewIn):
    draft: list[str] | None = None


class RubricIn(Strict):
    levels: Annotated[list[ShortText], Field(min_length=rubrics.LEVEL_COUNT, max_length=rubrics.LEVEL_COUNT)]
    interview: InterviewRecord


def settings_out(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "id"}


@router.get("/settings")
def get_settings(db: Database = Depends(get_db)):
    return settings_out(db.run(settings.get_settings))


@router.put("/settings")
def put_settings(body: SettingsPatch, db: Database = Depends(get_db)):
    fields = body.model_dump(exclude_none=True)
    return settings_out(db.run(lambda c: settings.update_settings(c, fields)))


@router.post("/settings/onboarding/complete")
def complete_onboarding(body: OnboardingIn, db: Database = Depends(get_db)):
    return settings_out(db.run(lambda c: settings.complete_onboarding(c, body.skipped)))


@router.get("/rubrics")
def list_rubrics(active: bool = False, db: Database = Depends(get_db)):
    items = db.run(lambda c: rubrics.list_rubrics(c, active))
    return {"items": items, "total": len(items)}


@router.post("/rubrics/interview")
def interview(body: InterviewIn, db: Database = Depends(get_db), ai: AIClient = Depends(get_ai)):
    return {"ai_status": "ok", "draft": rubrics.interview(db, ai, body.model_dump())}


@router.post("/rubrics", status_code=201)
def confirm_rubric(body: RubricIn, db: Database = Depends(get_db)):
    answers = body.interview.model_dump(exclude={"draft"})
    row = db.run(lambda c: rubrics.confirm(c, body.levels, answers, body.interview.draft))
    return {"id": row["id"], "version": row["version"]}
