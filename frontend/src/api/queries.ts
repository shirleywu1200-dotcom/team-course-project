// Dev-A 三頁共用的查詢鍵與讀取函式。查詢鍵集中在這裡，失效規則才有單一來源。

import { api } from "./client";
import type { Paged, ReasonsMeta, Task } from "./types";

export { keys } from "./queryKeys";

export const fetchReasons = () => api<ReasonsMeta>("/meta/reasons");

export const fetchTask = async (id: number) => (await api<{ task: Task }>(`/tasks/${id}`)).task;

export const fetchProjectTasks = async (projectId: number) =>
  (await api<Paged<Task>>(`/tasks?project_id=${projectId}`)).items;
