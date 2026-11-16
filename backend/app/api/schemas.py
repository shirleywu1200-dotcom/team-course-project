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
