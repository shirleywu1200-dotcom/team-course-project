// Dev-A 三頁共用的查詢鍵與讀取函式。查詢鍵集中在這裡，失效規則才有單一來源。

import { api } from "./client";
import type { Paged, ReasonsMeta, Task } from "./types";

export const keys = {
  reasons: ["meta", "reasons"] as const,
  task: (id: number) => ["tasks", id] as const,
  projectTasks: (projectId: number) => ["tasks", "project", projectId] as const,
};

export const fetchReasons = () => api<ReasonsMeta>("/meta/reasons");

export const fetchTask = async (id: number) => (await api<{ task: Task }>(`/tasks/${id}`)).task;

export const fetchProjectTasks = async (projectId: number) =>
  (await api<Paged<Task>>(`/tasks?project_id=${projectId}`)).items;
