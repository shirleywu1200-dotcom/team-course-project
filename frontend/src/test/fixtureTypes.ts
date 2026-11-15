// 形狀取自後端現況，待 Dev-A 補 response_model 後改由生成型別取代
// 僅限 src/test/；禁止從 src/api/ 匯出或由產品程式引用。
import type { EventRow, Task, TaskCreate } from "../api/types";

// backend/app/api/serialize.py：task_out 的 19 個欄位。
export interface SerializedTaskFixture extends Task {
  done_when: string;
  remind: NonNullable<TaskCreate["remind"]>;
  expected_stars: number;
  star_source: "self" | "ai_accepted" | "ai_edited" | "import_default";
  rubric_id: number | null;
  goal_id: number | null;
}

// backend/app/api/serialize.py：event_out 的 21 個欄位。
export interface SerializedEventFixture extends EventRow {
  ts: string;
  project_id: number | null;
  task_id: number | null;
  task_title: string;
  origin: string;
  origin_ref: number | null;
  source_id: number | null;
  note: string | null;
  ref_event_id: number | null;
  actor: string;
  extra: Record<string, unknown> | null;
}

// backend/app/api/routes_tasks.py：POST /tasks/{task_id}/status。
export interface StatusFixtureResponse {
  task: SerializedTaskFixture;
  event: SerializedEventFixture;
}

// 待 Dev-A 實作（todo 2.11）：FR-TSK-08、AC-62。
// 只列明文欄位；保留規劃中的 start_date，不猜測如何與現況 start 統一。
export interface AdjustStartFixtureRequest {
  new_start: string;
  expected_version: number;
  note?: string;
}

export interface AdjustStartFixtureResponse {
  task: { id: number; start_date: string; orig_due: string; latest_due: string; version: number };
  event: {
    id: number;
    kind: "task";
    field: "start_date";
    from_value: string;
    to_value: string;
    mine: boolean;
    mark: null;
    delta_days: null;
  };
  warnings: "START_AFTER_DUE"[];
}
