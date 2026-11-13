// 暫代 Dev-C todo 0.8（由 OpenAPI 產生型別）：先手寫 Dev-A 三頁需要的型別，0.8 完成後改用產生的型別。

export const OWNER_ME = "我";

export type Mark = "better" | "worse" | "none";
export type Direction = "earlier" | "later";

export interface Task {
  id: number;
  project_id: number | null;
  title: string;
  owner: string;
  scope: "work" | "private";
  start: string;
  orig_due: string;
  latest_due: string;
  delta_days: number;
  status: "todo" | "doing" | "done";
  blocked: boolean;
  done_date: string | null;
  version: number;
}

export interface EventRow {
  id: number;
  kind: string;
  field: string;
  from_value: string | null;
  to_value: string | null;
  delta_days: number | null;
  mark: Mark | null;
  reason: string | null;
  mine: boolean;
  batch_id: number | null;
}

export interface DueReason {
  code: string;
  label: string;
  direction: Direction;
  external: boolean;
}

export interface CodeLabel {
  code: string;
  label: string;
}

export interface ReasonsMeta {
  due: DueReason[];
  baseline_types: CodeLabel[];
  baseline_reasons: CodeLabel[];
}

export interface AdjustDueResult {
  task: Task;
  event: EventRow;
  warnings: string[];
  needs_mark: boolean;
}

export interface BulkPreviewRow {
  task_id: number;
  title: string;
  owner: string;
  from: string;
  to: string;
  mine: boolean;
  warnings: string[];
}

export interface BulkPreview {
  items: BulkPreviewRow[];
  mine_count: number;
  mark_required: boolean;
}

export interface BulkCommitResult {
  batch_id: number;
  updated: number;
  mine_marked: number;
  events: number[];
}

export interface FromTo<T> {
  from: T;
  to: T;
}

export interface BaselinePreview {
  confirmation_token: string;
  expires_at: string;
  impact: {
    orig_due: FromTo<string>;
    gap_days: FromTo<number>;
    project_delayed_count: FromTo<number>;
    past_due_events_kept: number;
    old_value_kept_in_history: boolean;
  };
}

export interface Paged<T> {
  items: T[];
  total: number;
}
