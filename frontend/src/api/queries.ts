// Dev-A 三頁與 Dev-B 收件匣（12.8）、匯入（12.7）、設定（12.11）共用的讀取函式；查詢鍵集中在 queryKeys.ts，失效規則才有單一來源。

import { api } from "./client";
import type { AppSettings, Candidate, IngestJob, Paged, Project, ReasonsMeta, Rubric, Task } from "./types";
import type { paths } from "./types.generated";
import { normalizeTimeManagementFilter, type StatsFilter } from "./queryKeys";

export { keys } from "./queryKeys";

export const fetchReasons = () => api<ReasonsMeta>("/meta/reasons");

export const fetchTask = async (id: number) => (await api<{ task: Task }>(`/tasks/${id}`)).task;

export const fetchProjectTasks = async (projectId: number) =>
  (await api<Paged<Task>>(`/tasks?project_id=${projectId}`)).items;

export const fetchCandidates = async (state: Candidate["state"]) =>
  (await api<Paged<Candidate>>(`/candidates?state=${state}`)).items;

export const fetchSettings = () => api<AppSettings>("/settings");

export const fetchIngestJob = (id: number) => api<IngestJob>(`/ingest/jobs/${id}`);

// 回傳 API 原形：快取鍵 keys.projectList() 與其他頁共用，形狀必須一致
export const fetchProjects = () => api<Paged<Project>>("/projects");

export const fetchActiveRubric = async () => (await api<Paged<Rubric>>("/rubrics?active=true")).items
  .reduce<Rubric | null>((latest, item) => !latest || item.version > latest.version ? item : latest, null);

export type TimeManagementStats = paths["/api/v1/stats/time-management"]["get"]["responses"][200]["content"]["application/json"];

export async function fetchTimeManagement(filter: StatsFilter = {}): Promise<TimeManagementStats> {
  const search = new URLSearchParams(Object.entries(normalizeTimeManagementFilter(filter))).toString();
  const data = await api<TimeManagementStats>(`/stats/time-management${search ? `?${search}` : ""}`);
  // 驗證必要欄位，不補空白、不重算；異常回應交既有 ErrorBanner 呈現。
  const counts = [data?.better?.count, data?.better?.days, data?.worse?.count, data?.worse?.days,
    data?.none, data?.unmarked, data?.min_sample, data?.worse_by_energy?.high,
    data?.worse_by_energy?.mid, data?.worse_by_energy?.low, data?.worse_by_energy?.not_done];
  if (!data || !counts.every(value => Number.isInteger(value)) || typeof data.judgement_note !== "string" ||
      !(data.judgement === null || typeof data.judgement === "string")) {
    throw new Error("時間管理統計回應格式不符");
  }
  return data;
}
