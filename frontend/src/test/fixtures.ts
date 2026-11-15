import type { AdjustDue, AdjustDueResult, StatusChange, Task } from "../api/types";
import type { AdjustStartFixtureRequest, AdjustStartFixtureResponse, SerializedEventFixture, SerializedTaskFixture, StatusFixtureResponse, TaskDetailFixtureResponse } from "./fixtureTypes";
import { getErrorFixture, type ErrorFixtureCode } from "./errorFixtures";

// 原 makeTask 的值、欄位與覆寫方式原樣保留，只有一份基底資料。
export function makeTask(over: Partial<Task> = {}): Task {
  return {
    id: 4, project_id: 1, title: "確認驗收條件", owner: "我", scope: "work", start: "2026-11-14",
    orig_due: "2026-11-18", latest_due: "2026-11-18", delta_days: 0, status: "todo", blocked: false,
    done_date: null, version: 1, ...over,
  };
}

export function makeSerializedTask(over: Partial<SerializedTaskFixture> = {}): SerializedTaskFixture {
  return {
    ...makeTask(), done_when: "", remind: "morning", expected_stars: 3,
    star_source: "self", rubric_id: 1, goal_id: null, ...over,
  };
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

// 待 Dev-A 實作（todo 2.11）：這些是已指定契約的固定快照，不模擬後端狀態機。
const implementation = "待 Dev-A 實作（todo 2.11）" as const;
const startRequest: AdjustStartFixtureRequest = { new_start: "2026-11-17", expected_version: 4, note: "範例開始日調整" };
const startResponse: AdjustStartFixtureResponse = {
  task: { id: 3, start_date: "2026-11-17", orig_due: "2026-11-20", latest_due: "2026-11-20", version: 5 },
  event: { id: 91, kind: "task", field: "start_date", from_value: "2026-11-15", to_value: "2026-11-17", mine: true, mark: null, delta_days: null },
  warnings: [],
};

function startError(code: ErrorFixtureCode, request: AdjustStartFixtureRequest) {
  const fixture = getErrorFixture(code);
  return { request, response: fixture.body, status: fixture.status, implementation };
}

export const adjustStartFixtures = {
  success: { request: startRequest, response: startResponse, status: 200, implementation },
  afterDue: {
    request: { ...startRequest, new_start: "2026-11-21" },
    response: {
      task: { ...startResponse.task, start_date: "2026-11-21" },
      event: { ...startResponse.event, to_value: "2026-11-21" },
      warnings: ["START_AFTER_DUE"],
    } satisfies AdjustStartFixtureResponse,
    status: 200, implementation,
  },
  taskDone: startError("TASK_DONE", { ...startRequest }),
  noChange: startError("NO_CHANGE", { ...startRequest, new_start: "2026-11-15" }),
  outOfRange: startError("DATE_OUT_OF_RANGE", { ...startRequest, new_start: "2029-11-17" }),
  staleVersion: startError("STALE_VERSION", { ...startRequest, expected_version: 3 }),
  validationError: startError("VALIDATION_ERROR", { ...startRequest, new_start: "invalid-date" }),
};
