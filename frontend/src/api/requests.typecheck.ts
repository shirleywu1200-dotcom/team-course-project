// 編譯期契約測試：請求必填欄位與列舉須由 OpenAPI 決定。
import type { AdjustDue, Complete, TaskCreate } from "./types";

export const createRequest: TaskCreate = { title: "範例任務", due: "2026-11-18" };
export const adjustRequest: AdjustDue = { new_due: "2026-11-19", expected_version: 1 };
export const completeRequest: Complete = { expected_version: 1 };

// @ts-expect-error 缺少必要的 due。
export const missingDue: TaskCreate = { title: "範例任務" };
// @ts-expect-error 註記值不在 OpenAPI 列舉內。
export const invalidMark: AdjustDue = { new_due: "2026-11-19", expected_version: 1, mark: "guessed" };
// @ts-expect-error 完成請求須帶版本號。
export const missingVersion: Complete = {};
