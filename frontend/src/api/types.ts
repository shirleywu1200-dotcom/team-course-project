// 請求與回應均引用 OpenAPI 產物；保留既有名稱相容，不另寫資源欄位。
import type { components } from "./types.generated";

export const OWNER_ME = "我";

export type AdjustDue = components["schemas"]["AdjustDue"];
export type Annotation = components["schemas"]["Annotation"];
export type BaselineCommit = components["schemas"]["BaselineCommit"];
export type BlockChange = components["schemas"]["BlockChange"];
export type BulkItem = components["schemas"]["BulkItem"];
export type BulkShift = components["schemas"]["BulkShift"];
export type Complete = components["schemas"]["Complete"];
export type OwnerChange = components["schemas"]["OwnerChange"];
export type ProjectCreate = components["schemas"]["ProjectCreate"];
export type ProjectPatch = components["schemas"]["ProjectPatch"];
export type StatusChange = components["schemas"]["StatusChange"];
export type TaskCreate = components["schemas"]["TaskCreate"];
export type BaselinePreviewRequest = components["schemas"]["BaselinePreview"];

type Schema = components["schemas"];
export type Task = Schema["TaskOut"];
export type EventRow = Schema["EventOut"];
export type DueReason = Schema["DueReasonOut"];
export type CodeLabel = Schema["CodeLabelOut"];
export type ReasonsMeta = Schema["ReasonsOut"];
export type AdjustDueResult = Schema["AdjustDueOut"];
export type BulkPreviewRow = Schema["BulkPreviewItemOut"];
export type BulkPreview = Schema["BulkPreviewOut"];
export type BulkCommitResult = Schema["BulkCommitOut"];
export type BaselinePreview = Schema["BaselinePreviewOut"];
export type Mark = NonNullable<EventRow["mark"]>;
export type Direction = DueReason["direction"];
export type FromTo<T> = { [K in keyof Schema["FromToDate"]]: T };
export type Paged<T> = { [K in keyof Schema["TaskListOut"]]: K extends "items" ? T[] : Schema["TaskListOut"][K] };
export type AdjustStart = Schema["AdjustStart"];
