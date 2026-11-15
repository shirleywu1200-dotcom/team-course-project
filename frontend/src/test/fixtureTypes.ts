// 所有 fixture 型別引用 A4 生成模型；僅保留舊測試匯出名稱相容。
import type { components } from "../api/types.generated";

type Schema = components["schemas"];
export type SerializedTaskFixture = Schema["TaskOut"];
export type SerializedEventFixture = Schema["EventOut"];
export type StatusFixtureResponse = Schema["TaskEventOut"];
export type TaskDetailFixtureResponse = Schema["TaskDetailOut"];
export type AdjustStartFixtureRequest = Schema["AdjustStart"];
export type AdjustStartFixtureResponse = Schema["AdjustStartOut"];
