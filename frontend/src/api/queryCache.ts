import type { QueryClient } from "@tanstack/react-query";
import { queryRoots } from "./queryKeys";

// 動作以 OpenAPI 現有操作為界；依據與查詢影響見 README 的 11.3 對照表。
export const mutationInvalidations = {
  "POST /projects": ["projects"],
  "PATCH /projects/{project_id}": ["projects"],
  "POST /projects/{project_id}/archive": ["projects"],
  "POST /projects/{project_id}/bulk-shift/preview": [],
  "POST /projects/{project_id}/bulk-shift/commit": ["tasks", "timeManagement", "gantt", "events"],
  "POST /tasks": ["tasks", "projects", "gantt", "events"],
  "PATCH /tasks/{task_id}/owner": ["tasks", "gantt", "events"],
  "POST /tasks/{task_id}/status": ["tasks", "gantt", "events"],
  "POST /tasks/{task_id}/block": ["tasks", "gantt", "events"],
  "POST /tasks/{task_id}/adjust-start": ["tasks", "gantt", "events"],
  "POST /tasks/{task_id}/complete": ["tasks", "timeManagement", "gantt", "events", "feedbackPending"],
  "POST /tasks/{task_id}/adjust-due": ["tasks", "timeManagement", "gantt", "events"],
  "POST /tasks/{task_id}/baseline-correction/preview": [],
  "POST /tasks/{task_id}/baseline-correction/commit": ["tasks", "projects", "gantt", "events"],
  "POST /events/{event_id}/annotations": ["tasks", "timeManagement", "events"],
  // Dev-B（12.7、12.8、12.11、Phase 8）：照各頁面現行的失效做法登記
  "POST /projects/import/preview": [],
  "POST /projects/import/commit": ["projects", "tasks", "gantt", "events"],
  "POST /ingest": ["candidates", "gantt"],
  "POST /candidates/{candidate_id}/confirm": ["candidates", "tasks", "timeManagement", "projects", "gantt", "events"],
  "POST /candidates/{candidate_id}/clarify": ["candidates", "tasks", "timeManagement", "projects", "gantt", "events"],
  "POST /candidates/{candidate_id}/create-task": ["candidates", "tasks", "timeManagement", "projects", "gantt", "events"],
  "POST /candidates/{candidate_id}/ignore": ["candidates", "tasks", "timeManagement", "projects", "gantt", "events"],
  "PUT /settings": ["settings"],
  "POST /settings/onboarding/complete": ["settings"],
  "POST /rubrics/interview": [],
  "POST /rubrics": ["rubrics"],
  "POST /sources/purge": ["candidates", "tasks", "events"],
  "POST /export": [],
  // 12.13 週報：H2 使用本次寫入回應替換快取，其他週報鍵只標 stale。
  "POST /reports/weekly/draft": ["weeklyReports"],
  "PUT /reports/weekly/{report_id}/manual": ["weeklyReports"],
  "PUT /tasks/{task_id}/feedback": ["tasks", "timeManagement", "events", "feedbackPending", "goals", "goalLinks"],
  "POST /goals": ["goals", "events"],
  "PATCH /goals/{goal_id}": ["goals", "events"],
  "POST /goals/{goal_id}/archive": ["goals", "events"],
  "POST /goal-links": ["tasks", "goals", "goalLinks", "gantt", "events"],
  "POST /goal-links/suggest": [],
  // 目標回報（9.10）：不改目標、統計、矩陣；回應由元件 setQueryData（#115），不失效，避免洗掉產生失敗的退路
  "POST /goals/{goal_id}/report/draft": [],
  "PUT /goals/{goal_id}/report/manual": [],
} as const satisfies Record<string, readonly (keyof typeof queryRoots)[]>;

export type MutationAction = keyof typeof mutationInvalidations;

// 呼叫者提供既有請求，不新增端點函式、認證管道或回應形狀。
// 失敗原樣拋回，STALE_VERSION 仍由現有頁面重讀並讓使用者重做。
export async function runMutationWithInvalidation<T>(client: QueryClient, action: MutationAction, write: () => Promise<T>): Promise<T> {
  const result = await write();
  await Promise.all(mutationInvalidations[action].map(resource => client.invalidateQueries({ queryKey: queryRoots[resource] })));
  return result;
}
