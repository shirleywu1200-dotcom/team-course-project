"""API 輸入模型（spec 第 5 章）。只做格式驗證；業務規則在 domain。"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Scope = Literal["work", "private"]
Audience = Literal["manager", "client", "none"]
Mark = Literal["better", "worse", "none"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ProjectCreate(Strict):
    name: str
    scope: Scope = "work"
    audience: Audience = "manager"
    line_group_id: int | None = None


class ProjectPatch(Strict):
    name: str | None = None
    scope: Scope | None = None
    audience: Audience | None = None


class TaskCreate(Strict):
    title: str
    due: date
    owner: str = "我"
    scope: Scope | None = None
    project_id: int | None = None
    start: date | None = None
    done_when: str = ""
    remind: Literal["morning", "eve_before", "none"] = "morning"
    goal_id: int | None = None
    expected_stars: int = Field(3, ge=1, le=5)
    suggested_stars: int | None = Field(None, ge=1, le=5)


class Versioned(Strict):
    expected_version: int


class OwnerChange(Versioned):
    owner: str


class StatusChange(Versioned):
    status: Literal["todo", "doing"]


class BlockChange(Versioned):
    blocked: bool = True


class AdjustStart(Versioned):
    new_start: date
    note: str | None = None


class Complete(Versioned):
    done_date: date | None = None


class AdjustDue(Versioned):
    new_due: date
    reason: str | None = None
    note: str | None = None
    mark: Mark | None = None
    defer_mark: bool = False


class Annotation(Strict):
    mark: Mark
    reason: str | None = None
    note: str | None = None


class BulkItem(Strict):
    task_id: int
    expected_version: int


class BulkShift(Strict):
    items: list[BulkItem]
    days: int
    reason: str | None = None
    note: str | None = None
    mark: Mark | None = None
    defer_mark: bool = False


class BaselinePreview(Versioned):
    new_orig_due: date
    type: Literal["correction", "rebaseline"]
    reason: str | None = None


class BaselineCommit(Strict):
    confirmation_token: str
    ack: bool = False


class WeeklyDraft(Strict):
    week_start: date


class ManualText(Strict):
    manual_text: str | None


# ---------- 完成回報（Phase 9，Dev-A；spec 5.12）----------

class FeedbackSave(Strict):
    """不收 goal_id（關聯走 POST /goal-links，#47 A6）；overdue_days 等伺服器欄位送了也忽略。"""
    actual_stars: int = Field(ge=1, le=5, strict=True)   # strict：true、"4" 不會被轉成整數
    energy: Literal["high", "mid", "low"]
    invest_vs_expected: Literal["less", "as_expected", "more"] | None = None
    rubric_id: int = Field(strict=True)


# ---------- 目標（Phase 9，Dev-A；spec 5.13）----------

GoalType = Literal["growth", "time", "expectation"]
Energy = Literal["high", "mid", "low"]


class GoalCreate(Strict):
    type: GoalType
    title: str
    period: str
    energy_plan: Energy
    definition: str = ""
    target: int = Field(0, ge=0)
    project_id: int | None = None


class GoalPatch(Strict):
    """type、project_id 建立後不可改，送了也忽略。"""
    title: str | None = None
    period: str | None = None
    definition: str | None = None
    target: int | None = Field(None, ge=0)
    energy_plan: Energy | None = None
