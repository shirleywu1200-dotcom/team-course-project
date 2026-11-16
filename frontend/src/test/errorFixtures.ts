import { HttpResponse } from "msw";

// spec 5.2 的唯一錯誤碼／HTTP 狀態資料集；訊息沿用舊 apiError 的 code。
export const errorDefinitions = [
  { status: 401, code: "UNAUTHORIZED" },
  { status: 404, code: "NOT_FOUND" },
  { status: 409, code: "TASK_DONE" },
  { status: 409, code: "STALE_VERSION" },
  { status: 409, code: "CONFIRMATION_INVALID" },
  { status: 409, code: "CANDIDATE_NOT_OPEN" },
  { status: 413, code: "PAYLOAD_TOO_LARGE" },
  { status: 422, code: "VALIDATION_ERROR" },
  { status: 422, code: "NO_CHANGE" },
  { status: 422, code: "DATE_OUT_OF_RANGE" },
  { status: 422, code: "MARK_REQUIRED" },
  { status: 422, code: "INCLUDES_DONE_TASK" },
  { status: 422, code: "EMPTY_SELECTION" },
  { status: 422, code: "ACK_REQUIRED" },
  { status: 422, code: "ANNOTATION_NOT_ALLOWED" },
  { status: 503, code: "AI_UNAVAILABLE" },
  // DA-19：待產品負責人複核。
  { status: 500, code: "INTERNAL_ERROR" },
] as const;

export type ErrorFixtureCode = typeof errorDefinitions[number]["code"];

export function getErrorFixture(code: ErrorFixtureCode) {
  const entry = errorDefinitions.find((definition) => definition.code === code)!;
  return {
    status: entry.status,
    body: { error: { code, message: code, details: {} } },
    review: code === "INTERNAL_ERROR" ? "待產品負責人複核" : null,
  };
}

// 保留舊三參數介面及輸出，讓 Dev-A 的測試不必修改。
export function apiError(status: number, code: string, details = {}) {
  return HttpResponse.json({ error: { code, message: code, details } }, { status });
}
