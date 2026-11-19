import type { AdjustDue, AdjustDueResult, StatusChange, Task } from "../api/types";
import type { components, paths } from "../api/types.generated";
import type { AdjustStartFixtureRequest, AdjustStartFixtureResponse, SerializedEventFixture, SerializedTaskFixture, StatusFixtureResponse, TaskDetailFixtureResponse } from "./fixtureTypes";
import { getErrorFixture, type ErrorFixtureCode } from "./errorFixtures";

// A4 TaskOut 的完整 19 欄；既有值保留，補上原 SerializedTaskFixture 的六個欄位。
export function makeTask(over: Partial<Task> = {}): Task {
  return {
    id: 4, project_id: 1, title: "確認驗收條件", owner: "我", scope: "work", start: "2026-11-14",
    orig_due: "2026-11-18", latest_due: "2026-11-18", delta_days: 0, status: "todo", blocked: false,
    done_date: null, done_when: "", remind: "morning", expected_stars: 3,
    star_source: "self", rubric_id: 1, goal_id: null, version: 1, ...over,
  };
}

export function makeSerializedTask(over: Partial<SerializedTaskFixture> = {}): SerializedTaskFixture {
  return makeTask(over);
}

export function makeTaskDetailFixture(): TaskDetailFixtureResponse {
  return { task: makeSerializedTask(), events: [] };
}

export function makeSerializedEvent(over: Partial<SerializedEventFixture> = {}): SerializedEventFixture {
  const task = makeTask();
  return {
    id: 9, ts: "2026-11-15T10:00:00+08:00", project_id: task.project_id,
    task_id: task.id, task_title: task.title, kind: "status", field: "status",
    from_value: "todo", to_value: "doing", origin: "manual", origin_ref: null, source_id: null,
    reason: null, note: null, delta_days: null, mark: null, mine: true,
    ref_event_id: null, batch_id: null, actor: "me", extra: null, ...over,
  };
}

// 12.9：日期與計數沿用伺服器快照；測試不以瀏覽器日期或本地公式產生。
export const todayFixtures = {
  today: { today: "2026-11-19" } satisfies components["schemas"]["TodayOut"],
  tasks: {
    items: [
      makeTask({ id: 101, title: "逾期範例", status: "todo", latest_due: "2026-11-18", version: 3, expected_stars: 4 }),
      makeTask({ id: 102, title: "今日範例", status: "doing", latest_due: "2026-11-19", version: 2 }),
      makeTask({ id: 103, title: "已完成範例", status: "done", latest_due: "2026-11-19", done_date: "2026-11-19" }),
    ], total: 3,
  } satisfies components["schemas"]["TaskListOut"],
  pending: { items: [{ task_id: 103, title: "已完成範例", owner: "我", project_id: 1,
    done_date: "2026-11-19", orig_due: "2026-11-17", overdue_days: 2,
    expected_stars: 3, star_source: "self" }], total: 1 } satisfies components["schemas"]["PendingFeedbackOut"],
  emptyPending: { items: [], total: 0 } satisfies components["schemas"]["PendingFeedbackOut"],
  completed: {
    task: makeTask({ id: 101, title: "逾期範例", status: "done", done_date: "2026-11-19", version: 4 }),
    event: makeSerializedEvent({ id: 501, task_id: 101, task_title: "逾期範例", kind: "status", field: "status", to_value: "done" }),
    feedback_required: true,
  } satisfies components["schemas"]["CompleteOut"],
  feedback: {
    id: 701, task_id: 103, actual_stars: 4, energy: "mid", invest_vs_expected: null,
    overdue_days: 2, rubric_id: 1, created_at: "2026-11-19T10:00:00+08:00",
  } satisfies components["schemas"]["FeedbackOut"],
  savedFeedback: {
    feedback: { id: 702, task_id: 103, actual_stars: 5, energy: "low", invest_vs_expected: "less",
      overdue_days: 7, rubric_id: 1, created_at: "2026-11-19T10:00:00+08:00" },
    event: makeSerializedEvent({ id: 702, task_id: 103, kind: "feedback", field: "completion_feedback",
      from_value: null, to_value: "702", extra: null }),
  } satisfies components["schemas"]["FeedbackSaveOut"],
};

type HistoryItem = components["schemas"]["HistoryItemOut"];
type HistoryList = components["schemas"]["HistoryListOut"];
const originalDue = {
  ...makeSerializedEvent({ id: 201, task_title: "舊任務名稱", kind: "due", field: "latest_due",
    from_value: "2026-11-18", to_value: "2026-11-20", delta_days: 2, mark: "worse", mine: true }),
  project_name: "範例專案", effective_mark: "none",
  source: { label: "手動", quote: null, purged: false },
} satisfies HistoryItem;
export const historyFixtures = {
  marked: { items: [originalDue], total: 1 } satisfies HistoryList,
  unmarked: { items: [{ ...originalDue, id: 202, effective_mark: null, mark: null }], total: 1 } satisfies HistoryList,
  otherOwner: { items: [{ ...originalDue, id: 203, mine: false, effective_mark: null }], total: 1 } satisfies HistoryList,
  purged: { items: [{ ...originalDue, id: 204,
    source: { label: "收件來源", quote: null, purged: true } }], total: 1 } satisfies HistoryList,
  empty: { items: [], total: 0 } satisfies HistoryList,
};

export const overviewFixtures = {
  project: {
    id: 1, name: "範例專案", scope: "work", audience: "none", line_group_id: null,
    created_at: "2026-11-01T09:00:00+08:00", updated_at: "2026-11-02T09:00:00+08:00", archived_at: null,
    task_count: 1, baseline_saved_at: null,
  } satisfies components["schemas"]["ProjectDetailOut"],
  gantt: {
    range: { from: "2026-11-09", to: "2026-11-22" }, today: "2026-11-16",
    summary: { done: 1, total: 3, delayed: 1, open_candidates: 2 },
    rows: [
      { task_id: 101, title: "範例任務甲", owner: "我", status: "doing", start: "2026-11-09",
        orig_due: "2026-11-18", latest_due: "2026-11-20", delta_days: 2, done_date: null, blocked: true, version: 4 },
      { task_id: 102, title: "範例任務乙", owner: "範例協作者", status: "todo", start: "2026-11-10",
        orig_due: "2026-11-22", latest_due: "2026-11-17", delta_days: -5, done_date: null, blocked: false, version: 2 },
      { task_id: 103, title: "範例任務丙", owner: "我", status: "done", start: "2026-11-11",
        orig_due: "2026-11-14", latest_due: "2026-11-14", delta_days: 0, done_date: "2026-11-13", blocked: false, version: 3 },
    ],
  } satisfies components["schemas"]["GanttOut"],
  empty: {
    range: null, today: "2026-11-16", summary: { done: 0, total: 0, delayed: 0, open_candidates: 2 }, rows: [],
  } satisfies components["schemas"]["GanttOut"],
};

export const historyProjectFixture = {
  id: 1, name: "範例專案", scope: "work", audience: "none", line_group_id: null,
  created_at: "2026-11-01T09:00:00+08:00", updated_at: "2026-11-02T09:00:00+08:00", archived_at: null,
  task_count: 1, baseline_saved_at: null,
} satisfies components["schemas"]["ProjectDetailOut"];

function statusFixture(status: StatusChange["status"]) {
  return {
    request: { status, expected_version: 1 } satisfies StatusChange,
    response: {
      task: makeSerializedTask({ status, version: 2 }),
      event: makeSerializedEvent({ from_value: status === "doing" ? "todo" : "doing", to_value: status }),
    } satisfies StatusFixtureResponse,
  };
}

export const statusFixtures = { todo: statusFixture("todo"), doing: statusFixture("doing") };

function dueFixture(mine: boolean) {
  const reason = mine ? "underestimated" : "wait_external";
  return {
    // 代表使用者已明確選擇的測試情境，並非介面預填。
    request: { new_due: "2026-11-21", expected_version: 1, reason, mark: "none" } satisfies AdjustDue,
    response: {
      task: makeSerializedTask({ owner: mine ? "我" : "範例負責人", latest_due: "2026-11-21", delta_days: 3, version: 2 }),
      event: makeSerializedEvent({ kind: "due", field: "latest_due", from_value: "2026-11-18", to_value: "2026-11-21", delta_days: 3, mine, mark: mine ? "none" : null, reason }),
      warnings: mine ? [] : ["MARK_IGNORED"], needs_mark: false,
    } satisfies AdjustDueResult,
  };
}

export const dueFixtures = { success: dueFixture(true), markIgnored: dueFixture(false) };

// 正式 AdjustStartOut 的固定快照，不模擬後端狀態機。
const startRequest: AdjustStartFixtureRequest = { new_start: "2026-11-17", expected_version: 4, note: "範例開始日調整" };
const startResponse: AdjustStartFixtureResponse = {
  task: makeTask({ id: 3, start: "2026-11-17", orig_due: "2026-11-20", latest_due: "2026-11-20", version: 5 }),
  event: makeSerializedEvent({ id: 91, task_id: 3, kind: "task", field: "start_date", from_value: "2026-11-15", to_value: "2026-11-17", mine: true, mark: null, delta_days: null }),
  warnings: [],
};

function startError(code: ErrorFixtureCode, request: AdjustStartFixtureRequest) {
  const fixture = getErrorFixture(code);
  return { request, response: fixture.body, status: fixture.status };
}

export const adjustStartFixtures = {
  success: { request: startRequest, response: startResponse, status: 200 },
  afterDue: {
    request: { ...startRequest, new_start: "2026-11-21" },
    response: {
      task: { ...startResponse.task, start: "2026-11-21" },
      event: { ...startResponse.event, to_value: "2026-11-21" },
      warnings: ["START_AFTER_DUE"],
    } satisfies AdjustStartFixtureResponse,
    status: 200,
  },
  taskDone: startError("TASK_DONE", { ...startRequest }),
  noChange: startError("NO_CHANGE", { ...startRequest, new_start: "2026-11-15" }),
  outOfRange: startError("DATE_OUT_OF_RANGE", { ...startRequest, new_start: "2029-11-17" }),
  staleVersion: startError("STALE_VERSION", { ...startRequest, expected_version: 3 }),
  validationError: startError("VALIDATION_ERROR", { ...startRequest, new_start: "invalid-date" }),
};

// 12.10 定稿 §5：固定伺服器回應，不在 MSW 重算判讀；只引用生成型別。
type TimeMgmtStatsOut = paths["/api/v1/stats/time-management"]["get"]["responses"][200]["content"]["application/json"];
export const timeManagementFixtures = {
  insufficient: {
    better: { count: 1, days: 1 }, worse: { count: 3, days: 6 }, none: 1, unmarked: 1,
    worse_by_energy: { high: 0, mid: 1, low: 1, not_done: 1 }, min_sample: 5,
    judgement: null, judgement_note: "樣本 4 筆，不到 5 筆，只顯示不下結論",
  },
  better: {
    better: { count: 4, days: 8 }, worse: { count: 2, days: 3 }, none: 1, unmarked: 0,
    worse_by_energy: { high: 1, mid: 1, low: 0, not_done: 0 }, min_sample: 5,
    judgement: "時間管理偏向變好", judgement_note: "變好 4 次、變差 2 次。",
  },
  worseLowEnergy: {
    better: { count: 2, days: 3 }, worse: { count: 3, days: 9 }, none: 0, unmarked: 1,
    worse_by_energy: { high: 0, mid: 0, low: 2, not_done: 1 }, min_sample: 5,
    judgement: "偏向變差，建議檢視", judgement_note: "變好 2 次、變差 3 次。變差多集中在低精力任務。",
  },
  half: {
    better: { count: 1, days: 2 }, worse: { count: 4, days: 8 }, none: 0, unmarked: 0,
    worse_by_energy: { high: 0, mid: 2, low: 2, not_done: 0 }, min_sample: 5,
    judgement: "偏向變差，建議檢視", judgement_note: "變好 1 次、變差 4 次。",
  },
  balanced: {
    better: { count: 3, days: 6 }, worse: { count: 3, days: 7 }, none: 1, unmarked: 0,
    worse_by_energy: { high: 1, mid: 1, low: 0, not_done: 1 }, min_sample: 5,
    judgement: "持平", judgement_note: "變好 3 次、變差 3 次。",
  },
  notDone: {
    better: { count: 1, days: 1 }, worse: { count: 4, days: 8 }, none: 0, unmarked: 0,
    worse_by_energy: { high: 0, mid: 0, low: 0, not_done: 4 }, min_sample: 5,
    judgement: "偏向變差，建議檢視", judgement_note: "變好 1 次、變差 4 次。",
  },
  empty: {
    better: { count: 0, days: 0 }, worse: { count: 0, days: 0 }, none: 0, unmarked: 0,
    worse_by_energy: { high: 0, mid: 0, low: 0, not_done: 0 }, min_sample: 5,
    judgement: null, judgement_note: "樣本 0 筆，不到 5 筆，只顯示不下結論",
  },
  ac13: {
    better: { count: 1, days: 1 }, worse: { count: 1, days: 2 }, none: 1, unmarked: 1,
    worse_by_energy: { high: 0, mid: 0, low: 0, not_done: 1 }, min_sample: 5,
    judgement: null, judgement_note: "樣本 2 筆，不到 5 筆，只顯示不下結論",
  },
} satisfies Record<string, TimeMgmtStatsOut>;

export const dataControlFixtures = {
  exportEmpty: {
    exported_at: "2026-11-16T18:00:00+08:00", schema_version: "0003",
    counts: { settings: 0, sources: 0, events: 0, ai_runs: 0 },
    tables: { settings: [], sources: [], events: [], ai_runs: [] },
  } satisfies components["schemas"]["ExportOut"],
  purgedZero: { purged: 0 } satisfies components["schemas"]["PurgeOut"],
  purgedThree: { purged: 3 } satisfies components["schemas"]["PurgeOut"],
};
