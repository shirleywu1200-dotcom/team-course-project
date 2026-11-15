// 請求型別只引用 OpenAPI 產物；回應暫沿用 Dev-A 原有定義。
import type { components } from "./types.generated";

export * from "./types.pending";
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
