import { api } from "../../api/client";
import type { components, paths } from "../../api/types.generated";

export type WeeklyReport = components["schemas"]["WeeklyReportOut"];
export type WeeklyItem = components["schemas"]["WeeklyItemOut"];
type WeeklyDraft = NonNullable<paths["/api/v1/reports/weekly/draft"]["post"]["requestBody"]>["content"]["application/json"];
type ManualText = NonNullable<paths["/api/v1/reports/weekly/{report_id}/manual"]["put"]["requestBody"]>["content"]["application/json"];

export const fetchWeeklyByWeek = (weekStart: string) =>
  api<WeeklyReport>(`/reports/weekly?week_start=${encodeURIComponent(weekStart)}`);

export const fetchWeeklyById = (id: number) => api<WeeklyReport>(`/reports/weekly/${id}`);

export const generateWeeklyDraft = (body: WeeklyDraft) =>
  api<WeeklyReport>("/reports/weekly/draft", { body });

export const saveWeeklyManual = (id: number, body: ManualText) =>
  api<WeeklyReport>(`/reports/weekly/${id}/manual`, { method: "PUT", body });
