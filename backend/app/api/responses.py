"""API 回應模型（PR #1 審查 A4）：讓 OpenAPI 的 2xx 都有 schema，前端可由此產生型別。

形狀以 `serialize.py` 的實際輸出為準；這裡只描述，不改變回應內容。
欄位新增、改名或改 nullable 都屬契約變更，要同步通知 Dev-C 與 QC-2。
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Mark = Literal["better", "worse", "none"]


class Out(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


# ---------- 共用資源 ----------

class TaskOut(Out):
    id: int
    project_id: int | None
    title: str
    owner: str
    scope: Literal["work", "private"]
    start: date
    orig_due: date
    latest_due: date
    delta_days: int = Field(description="latest_due − orig_due（天）")
    status: Literal["todo", "doing", "done"]
    blocked: bool
    done_date: date | None
    done_when: str
    remind: Literal["morning", "eve_before", "none"]
    expected_stars: int
    star_source: Literal["self", "ai_accepted", "ai_edited", "import_default"]
    rubric_id: int | None
    goal_id: int | None
    version: int


class EventOut(Out):
    id: int
    ts: datetime
    project_id: int | None
    task_id: int | None
    task_title: str
    kind: Literal["due", "annotation", "status", "task", "feedback", "goal", "baseline", "project"]
    field: str
    from_value: str | None
    to_value: str | None
    origin: Literal["candidate", "manual", "bulk", "import", "baseline_correction", "system"]
    origin_ref: int | None
    source_id: int | None
    reason: str | None
    note: str | None
    delta_days: int | None
    mark: Mark | None
    mine: bool
    ref_event_id: int | None
    batch_id: int | None
    actor: str
    extra: dict | None


class ProjectOut(Out):
    id: int
    name: str
    scope: Literal["work", "private"]
    audience: Literal["manager", "client", "none"]
    line_group_id: int | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ProjectDetailOut(ProjectOut):
    task_count: int
    baseline_saved_at: datetime | None


# ---------- 專案 ----------

class ProjectListOut(Out):
    items: list[ProjectOut]
    total: int


class ProjectPatchOut(Out):
    project: ProjectOut
    changes: list[EventOut]


class BulkPreviewItemOut(Out):
    task_id: int
    title: str
    owner: str
    from_: date = Field(alias="from")
    to: date
    mine: bool
    warnings: list[str]


class BulkPreviewOut(Out):
    items: list[BulkPreviewItemOut]
    mine_count: int
    mark_required: bool


class BulkCommitOut(Out):
    batch_id: int
    updated: int
    mine_marked: int
    events: list[int]


# ---------- 任務 ----------

class TaskListOut(Out):
    items: list[TaskOut]
    total: int


class TaskDetailOut(Out):
    task: TaskOut
    events: list[EventOut]


class TaskEventOut(Out):
    task: TaskOut
    event: EventOut


class AdjustStartOut(TaskEventOut):
    warnings: list[str] = Field(description="可含 START_AFTER_DUE（開始日晚於最新預計日）")


class CompleteOut(TaskEventOut):
    feedback_required: bool


class AdjustDueOut(TaskEventOut):
    warnings: list[str]
    needs_mark: bool


class FromToDate(Out):
    from_: date = Field(alias="from")
    to: date


class FromToInt(Out):
    from_: int = Field(alias="from")
    to: int


class BaselineImpactOut(Out):
    orig_due: FromToDate
    gap_days: FromToInt
    project_delayed_count: FromToInt
    past_due_events_kept: int
    old_value_kept_in_history: bool


class BaselinePreviewOut(Out):
    confirmation_token: str
    expires_at: datetime
    impact: BaselineImpactOut


# ---------- 週報（Phase 10，Dev-A；spec 5.14）----------

class WeeklyItemOut(Out):
    section: Literal["done", "delay", "next"]
    task_id: int
    event_id: int | None = Field(description="next 項目為 null")


class WeeklyReportOut(Out):
    id: int
    week_start: date
    ai_status: Literal["ok", "unavailable", "invalid_output"] | None
    excluded_private: int = Field(description="產生初稿當下送 AI 前排除的私人任務數（AC-48）")
    draft: str | None = Field(description="validated=false 時為 null")
    items: list[WeeklyItemOut] = Field(description="validated=true 為 AI 項目，否則為依歷程列出的事件清單")
    validated: bool
    manual_text: str | None
    updated_at: datetime


# ---------- 註記、統計、選項、健康檢查 ----------

class AnnotationOut(Out):
    event: EventOut
    effective_mark: Mark


class CountDays(Out):
    count: int
    days: int


class EnergyDistribution(Out):
    high: int
    mid: int
    low: int
    not_done: int


class TimeMgmtStatsOut(Out):
    better: CountDays
    worse: CountDays
    none: int
    unmarked: int
    worse_by_energy: EnergyDistribution
    min_sample: int
    judgement: str | None = Field(description="樣本不足 min_sample 時為 null；規則見 spec FR-MRK-07")
    judgement_note: str = Field(description="判讀說明：樣本不足的說明，或變好／變差次數＋精力洞察（FR-MRK-07）")


class DueReasonOut(Out):
    code: str
    label: str
    direction: Literal["earlier", "later"]
    external: bool


class CodeLabelOut(Out):
    code: str
    label: str


class ReasonsOut(Out):
    due: list[DueReasonOut]
    baseline_types: list[CodeLabelOut]
    baseline_reasons: list[CodeLabelOut]


class HealthOut(Out):
    db: Literal["ok", "error"]
    ai: Literal["ok", "unavailable"]
