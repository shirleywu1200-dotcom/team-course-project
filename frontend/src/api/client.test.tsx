import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { useEffect, useState } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { ErrorBanner } from "../components/standin/ErrorBanner";
import { TaskDuePage } from "../features/due-adjust/TaskDuePage";
import { API, makeTask, renderWithClient, server } from "../test/server";
import { api, ApiError, getToken, setToken } from "./client";
import type { AdjustDue } from "./types";

const errors = [
  [401, "UNAUTHORIZED", "存取 token 錯誤或未設定。"],
  [404, "NOT_FOUND", "找不到指定資料。"],
  [409, "TASK_DONE", "這個任務已完成，不能再調整。"],
  [409, "STALE_VERSION", "資料已被其他操作更新，已重新載入，請確認後再操作一次。"],
  [409, "CONFIRMATION_INVALID", "確認憑證已過期、已使用，或任務已變動，請重新預覽。"],
  [409, "CANDIDATE_NOT_OPEN", "候選已處理。"],
  [413, "PAYLOAD_TOO_LARGE", "資料超過允許大小。"],
  [422, "VALIDATION_ERROR", "請檢查輸入欄位。"],
  [422, "NO_CHANGE", "新日期與目前相同，不需要調整。"],
  [422, "DATE_OUT_OF_RANGE", "日期超出允許範圍（今天前 365 天到後 730 天）。"],
  [422, "MARK_REQUIRED", "這是你的任務，請選擇時間管理註記，或選「稍後註記」。"],
  [422, "INCLUDES_DONE_TASK", "勾選的任務中有已完成任務，請取消勾選。"],
  [422, "EMPTY_SELECTION", "請至少勾選一項任務。"],
  [422, "ACK_REQUIRED", "請先勾選聲明再確認。"],
  [422, "ANNOTATION_NOT_ALLOWED", "這筆事件不可補註記。"],
  [503, "AI_UNAVAILABLE", "AI 暫時無法使用。"],
  // DA-19：待產品負責人複核。
  [500, "INTERNAL_ERROR", "伺服器內部錯誤，請稍後再試。"],
] as const;

function ErrorView({ onError }: { onError: (error: unknown) => void }) {
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    void api("/tasks/4").catch((failure: unknown) => {
      onError(failure);
      setError(failure);
    });
  }, [onError]);
  return <ErrorBanner error={error} />;
}

beforeEach(() => localStorage.removeItem("g4.token"));
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  localStorage.removeItem("g4.token");
});

test.each(errors)("%i %s：解析統一錯誤、顯示訊息且不自動重送", async (status, code, message) => {
  server.use(http.get(`${API}/tasks/4`, () => HttpResponse.json({
    error: { code, message, details: { task_id: 4 } },
  }, { status })));
  const captured = vi.fn();
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  renderWithClient(<ErrorView onError={captured} />);
  expect(await screen.findByRole("alert")).toHaveTextContent(message);
  expect(captured).toHaveBeenCalledWith(expect.any(ApiError));
  expect(captured.mock.calls[0][0]).toMatchObject({ status, code, message, details: { task_id: 4 } });
  expect(fetchSpy).toHaveBeenCalledTimes(1);
});

test.each([200, 201])("HTTP %i 當作成功，原樣回傳 JSON 與 MARK_IGNORED 警告", async (status) => {
  // 測試通用 client 的 HTTP 成功判斷，不新增建立端點或回應型別。
  const data = { task: makeTask(), warnings: ["MARK_IGNORED"] };
  server.use(http.get(`${API}/tasks/4`, () => HttpResponse.json(data, { status })));
  await expect(api("/tasks/4")).resolves.toEqual(data);
});

test("沿用 localStorage token、Bearer、JSON 與 Idempotency-Key 傳送方式", async () => {
  setToken("fixture-token");
  expect(localStorage.getItem("g4.token")).toBe("fixture-token");
  expect(getToken()).toBe("fixture-token");
  const body: AdjustDue = { new_due: "2026-11-21", expected_version: 1, mark: "none" };
  const received = vi.fn();
  server.use(http.post(`${API}/tasks/4/adjust-due`, async ({ request }) => {
    received({
      authorization: request.headers.get("Authorization"),
      contentType: request.headers.get("Content-Type"),
      key: request.headers.get("Idempotency-Key"),
      body: await request.json(),
    });
    return HttpResponse.json({});
  }));
  await api("/tasks/4/adjust-due", { body, idempotencyKey: "fixture-request" });
  expect(received).toHaveBeenCalledExactlyOnceWith({
    authorization: "Bearer fixture-token", contentType: "application/json", key: "fixture-request", body,
  });
});

test("環境變數作為備援，既有本機 token 優先；GET 不帶 JSON 本文", async () => {
  vi.stubEnv("VITE_API_TOKEN", "fixture-env");
  expect(getToken()).toBe("fixture-env");
  setToken("fixture-local");
  expect(getToken()).toBe("fixture-local");
  const received = vi.fn();
  server.use(http.get(`${API}/tasks/4`, async ({ request }) => {
    received(request.headers.get("Authorization"), request.headers.get("Content-Type"), await request.text());
    return HttpResponse.json({ task: makeTask() });
  }));
  await api("/tasks/4", { method: "GET" });
  expect(received).toHaveBeenCalledExactlyOnceWith("Bearer fixture-local", null, "");
});

test("localStorage 不可存取時沿用環境變數備援，不更改儲存策略", () => {
  vi.stubEnv("VITE_API_TOKEN", "fixture-env");
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("unavailable"); });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("unavailable"); });
  expect(getToken()).toBe("fixture-env");
  expect(() => setToken("fixture-local")).not.toThrow();
});

test.each([
  null,
  { error: null },
  { error: { code: 42, message: { invalid: true }, details: [] } },
  { error: { code: "", message: "", details: null } },
])("錯誤格式異常 %j：提供有效字串與物件備援", async (body) => {
  server.use(http.get(`${API}/tasks/4`, () => HttpResponse.json(body, { status: 422, statusText: "" })));
  await expect(api("/tasks/4")).rejects.toMatchObject({
    status: 422, code: "HTTP_ERROR", message: "Unprocessable Entity", details: {},
  });
});

test("HTTP 沒有狀態文字時仍有可顯示的備援訊息", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 422, statusText: "" }));
  await expect(api("/tasks/4")).rejects.toMatchObject({
    status: 422, code: "HTTP_ERROR", message: "HTTP 422", details: {},
  });
});

test("非 JSON 錯誤回應不把 HTML 原文帶入錯誤訊息", async () => {
  server.use(http.get(`${API}/tasks/4`, () => HttpResponse.text("<html>upstream error</html>", {
    status: 502, statusText: "Bad Gateway",
  })));
  await expect(api("/tasks/4")).rejects.toMatchObject({
    status: 502, code: "HTTP_ERROR", message: "Bad Gateway", details: {},
  });
});

test("STALE_VERSION 實際重讀任務，不自動重送；使用者重做才帶新版本提交", async () => {
  let reads = 0;
  const bodies: AdjustDue[] = [];
  server.use(
    http.get(`${API}/tasks/4`, () => {
      reads += 1;
      return HttpResponse.json({ task: makeTask(reads === 1 ? {} : { latest_due: "2026-11-20", version: 2 }) });
    }),
    http.post(`${API}/tasks/4/adjust-due`, async ({ request }) => {
      bodies.push(await request.json() as AdjustDue);
      if (bodies.length === 1) return HttpResponse.json({ error: { code: "STALE_VERSION", message: "版本已變更", details: {} } }, { status: 409 });
      return HttpResponse.json({ task: makeTask({ latest_due: "2026-11-21", version: 3 }), warnings: [], needs_mark: false });
    }),
  );
  const user = userEvent.setup();
  renderWithClient(<MemoryRouter initialEntries={["/tasks/4"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <Routes><Route path="/tasks/:taskId" element={<TaskDuePage />} /></Routes>
  </MemoryRouter>);
  await screen.findByRole("heading", { name: "確認驗收條件", level: 1 });
  fireEvent.change(screen.getByLabelText("新的預計完成日"), { target: { value: "2026-11-21" } });
  await screen.findByRole("option", { name: "估計不準（我低估）" });
  await user.selectOptions(screen.getByLabelText("原因"), "underestimated");
  await user.click(screen.getByRole("radio", { name: "不計入" }));
  await user.click(screen.getByRole("button", { name: "確認調整" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("請確認後再操作一次");
  await waitFor(() => expect(screen.getByTestId("delta")).toHaveTextContent("2026-11-20 → 2026-11-21"));
  expect(reads).toBe(2);
  expect(bodies).toHaveLength(1);
  expect(bodies[0].expected_version).toBe(1);
  await user.click(screen.getByRole("button", { name: "確認調整" }));
  await screen.findByRole("status");
  expect(bodies).toHaveLength(2);
  expect(bodies[1].expected_version).toBe(2);
});
