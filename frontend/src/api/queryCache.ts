import type { QueryClient } from "@tanstack/react-query";
import { queryRoots } from "./queryKeys";

// 動作以 OpenAPI 現有操作為界；依據與查詢影響見 README 的 11.3 對照表。
export const mutationInvalidations = {
  "POST /projects": ["projects"],
  "PATCH /projects/{project_id}": ["projects"],
  "POST /projects/{project_id}/archive": ["projects"],
  "POST /projects/{project_id}/bulk-shift/preview": [],
  "POST /projects/{project_id}/bulk-shift/commit": ["tasks", "timeManagement"],
  "POST /tasks": ["tasks", "projects"],
  "PATCH /tasks/{task_id}/owner": ["tasks"],
  "POST /tasks/{task_id}/status": ["tasks"],
  "POST /tasks/{task_id}/block": ["tasks"],
  "POST /tasks/{task_id}/adjust-start": ["tasks"],
  "POST /tasks/{task_id}/complete": ["tasks", "timeManagement"],
  "POST /tasks/{task_id}/adjust-due": ["tasks", "timeManagement"],
  "POST /tasks/{task_id}/baseline-correction/preview": [],
  "POST /tasks/{task_id}/baseline-correction/commit": ["tasks", "projects"],
  "POST /events/{event_id}/annotations": ["tasks", "timeManagement"],
  // Dev-B（12.7、12.8、12.11、Phase 8）：照各頁面現行的失效做法登記
  "POST /projects/import/preview": [],
  "POST /projects/import/commit": ["projects", "tasks"],
  "POST /ingest": ["candidates"],
  "POST /candidates/{candidate_id}/confirm": ["candidates", "tasks", "timeManagement", "projects"],
  "POST /candidates/{candidate_id}/clarify": ["candidates", "tasks", "timeManagement", "projects"],
  "POST /candidates/{candidate_id}/create-task": ["candidates", "tasks", "timeManagement", "projects"],
  "POST /candidates/{candidate_id}/ignore": ["candidates", "tasks", "timeManagement", "projects"],
  "PUT /settings": ["settings"],
  "POST /settings/onboarding/complete": ["settings"],
  "POST /rubrics/interview": [],
  "POST /rubrics": ["rubrics"],
  "POST /sources/purge": ["candidates", "tasks"],
  "POST /export": [],
  // Dev-A（Phase 10 週報後端）：前端尚無讀週報的查詢，先登記為無；12.9 建立週報查詢鍵時由 Dev-C 改寫
  "POST /reports/weekly/draft": [],
  "PUT /reports/weekly/{report_id}/manual": [],
} as const satisfies Record<string, readonly (keyof typeof queryRoots)[]>;

export type MutationAction = keyof typeof mutationInvalidations;

// 呼叫者提供既有請求，不新增端點函式、認證管道或回應形狀。
// 失敗原樣拋回，STALE_VERSION 仍由現有頁面重讀並讓使用者重做。
export async function runMutationWithInvalidation<T>(client: QueryClient, action: MutationAction, write: () => Promise<T>): Promise<T> {
  const result = await write();
  await Promise.all(mutationInvalidations[action].map(resource => client.invalidateQueries({ queryKey: queryRoots[resource] })));
  return result;
}
