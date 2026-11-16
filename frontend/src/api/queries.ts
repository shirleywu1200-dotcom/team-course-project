// Dev-A 三頁與 Dev-B 收件匣（12.8）、匯入（12.7）、設定（12.11）共用的讀取函式；查詢鍵集中在 queryKeys.ts，失效規則才有單一來源。

import { api } from "./client";
import type { AppSettings, Candidate, IngestJob, Paged, Project, ReasonsMeta, Rubric, Task } from "./types";

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

export const fetchActiveRubric = async () => (await api<Paged<Rubric>>("/rubrics?active=true")).items[0];
