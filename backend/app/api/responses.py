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

class WeeklyEventOut(Out):
    """事件證據：只有時間與前值、後值、天數；不含原因、備註、註記與原句（spec 5.14）。"""
    id: int
    ts: datetime
    from_value: str | None
    to_value: str | None
    delta_days: int | None


class WeeklyItemOut(Out):
    """不屬於該段的欄位為 null（spec 5.14 表）；可讀內容是讀取時的任務現值。"""
    section: Literal["done", "delay", "next"]
    task_id: int
    event_id: int | None = Field(description="next 項目為 null")
    title: str | None
    owner: str | None
    done_date: date | None = Field(description="只有 done")
    orig_due: date | None = Field(description="只有 delay")
    latest_due: date | None = Field(description="delay、next")
    blocked: bool | None = Field(description="只有 next")
    event: WeeklyEventOut | None = Field(description="done 為完成事件、delay 為延後事件；next 為 null")


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


# ---------- 歷程與甘特（Phase 5，Dev-B） ----------

class SourceRefOut(Out):
    label: str
    quote: str | None = Field(description="原文已清除或沒有來源時為 null")
    purged: bool


class HistoryItemOut(EventOut):
    project_name: str | None
    effective_mark: Mark | None
    source: SourceRefOut


class HistoryListOut(Out):
    items: list[HistoryItemOut]
    total: int


class GanttSummary(Out):
    done: int
    total: int
    delayed: int
    open_candidates: int


class GanttRowOut(Out):
    task_id: int
    title: str
    owner: str
    status: Literal["todo", "doing", "done"]
    start: date
    orig_due: date
    latest_due: date
    delta_days: int
    done_date: date | None
    blocked: bool
    version: int


class GanttOut(Out):
    range: FromToDate | None = Field(description="沒有任務時為 null")
    today: date
    summary: GanttSummary
    rows: list[GanttRowOut]


# ---------- 匯入（Phase 6，Dev-B） ----------

AiStatus = Literal["ok", "unavailable", "invalid_output"]


class ImportIssueOut(Out):
    level: Literal["error", "warn"]
    code: str
    message: str


class ImportRowOut(Out):
    index: int
    title: str
    owner: str
    start: date | None
    end: date | None
    blocking: bool
    issues: list[ImportIssueOut]


class ColumnMapOut(Out):
    title: int | None
    owner: int | None
    start: int | None
    end: int | None
    mapped_by: Literal["rule", "ai", "manual"] | None = Field(description="必填欄位對應不到時為 null，rows 為空")
    ai_run_id: int | None = Field(
        None, description="mapped_by 為 ai 時才出現；commit 時與 column_map 一起送回（12.7 D-3）")


class ImportSummary(Out):
    importable: int
    blocking: int


class ImportPreviewOut(Out):
    ai_status: AiStatus
    header: list[str]
    column_map: ColumnMapOut
    rows: list[ImportRowOut]
    summary: ImportSummary


class ImportCommitOut(Out):
    project_id: int
    created: int
    skipped: int
    event_id: int


# ---------- 收件與候選（Phase 7，Dev-B） ----------
# 選填欄位（沒有就不出現）的端點以 response_model_exclude_unset=True 註冊，維持原本的回應形狀。

class CandidateTaskOut(Out):
    id: int
    title: str
    latest_due: date
    orig_due: date
    version: int


class ProposedOut(Out):
    new_due: date | None = None


class SuggestOut(Out):
    kind: Literal["delay", "done", "stuck"]
    new_due: date | None = None


class CandidateOut(Out):
    id: int
    kind: Literal["delay", "done", "stuck", "unclear", "unmatched"]
    certainty: Literal["sure", "to_clarify", "to_match"]
    state: Literal["open", "confirmed", "ignored"]
    task: CandidateTaskOut | None
    proposed: ProposedOut | None
    quote: str | None = Field(description="原文已清除時為 null")
    speaker: str
    spoken_at: str | None
    note: str | None
    suggest: SuggestOut | None


class CandidateListOut(Out):
    items: list[CandidateOut]
    total: int


class IngestSummary(Out):
    created: int
    skipped: int
    duplicates: int
    unparsed_lines: list[int]


class IngestSyncOut(Out):
    mode: Literal["sync"]
    ai_status: AiStatus
    result: IngestSummary
    candidates: list[CandidateOut]


class IngestAsyncOut(Out):
    mode: Literal["async"]
    job_id: int
    status: Literal["queued"]


class IngestJobResult(IngestSummary):
    ai_status: AiStatus
    candidate_ids: list[int]


class IngestJobOut(Out):
    id: int
    status: Literal["queued", "running", "succeeded", "failed"]
    attempts: int
    result: IngestJobResult | None
    error: str | None


class DecideOut(Out):
    candidate: CandidateOut
    task: TaskOut | None = Field(None, description="忽略時不出現")
    event: EventOut | None = Field(None, description="忽略、建任務時不出現")
    needs_mark: bool | None = Field(None, description="確認延期時才出現")
    warnings: list[str] | None = Field(None, description="確認延期時才出現；可含 BEFORE_START（新日期早於開始日）")
    feedback_required: bool | None = Field(None, description="確認完成時才出現")


# ---------- 設定、量表、資料控制（Phase 8，Dev-B） ----------

class SettingsOut(Out):
    default_scope: Literal["work", "private"]
    role: Literal["project_owner", "wbs_owner", "both"]
    report_audience: Literal["manager", "client", "none"]
    confirm_time: str
    confirm_cap_min: int
    remind_default: Literal["morning", "eve_before", "none"]
    retention_days: int
    energy_def_high: str
    energy_def_mid: str
    energy_def_low: str
    goal_types_enabled: list[Literal["growth", "time", "expectation"]]
    onboarded_at: datetime | None


class InterviewAnswers(Out):
    q1: str
    q2: str
    q3: str


class RubricOut(Out):
    id: int
    version: int
    levels: list[str]
    source: Literal["default", "interview"]
    interview: InterviewAnswers | None
    created_at: datetime


class RubricListOut(Out):
    items: list[RubricOut]
    total: int


class RubricCreatedOut(Out):
    id: int
    version: int


class RubricDraftOut(Out):
    ai_status: Literal["ok"]
    draft: list[str]


class PurgeOut(Out):
    purged: int


class ExportOut(Out):
    exported_at: datetime
    schema_version: str | None
    counts: dict[str, int]
    tables: dict[str, list[dict]]
