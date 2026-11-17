import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { http, HttpResponse } from "msw";

import { App } from "../../App";
import { API, renderWithClient, server } from "../../test/server";
import { weeklyEmpty, weeklyInvalidOutput, weeklyReady, weeklyReconciliationFailed, weeklyUnavailable } from "../../test/weeklyFixtures";
import { WeeklyReportPage } from "./WeeklyReportPage";
import { currentWeekStart } from "./weeklyState";

function open(path = "/reports?week_start=2026-11-09") {
  return renderWithClient(<MemoryRouter initialEntries={[path]}>
    <Routes><Route path="/reports" element={<><WeeklyReportPage /><Link to="/history">離開週報</Link><LocationProbe /></>} /><Route path="/history" element={<p>歷程頁</p>} /></Routes>
  </MemoryRouter>);
}

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.search}</output>;
}

test("L1：按週 GET 404 是未產生，請求數至多 2；不自動 POST", async () => {
  let gets = 0;
  let posts = 0;
  server.use(
    http.get(`${API}/reports/weekly`, () => { gets++; return HttpResponse.json({ error: { code: "NOT_FOUND", message: "未產生", details: { week_start: "2026-11-09" } } }, { status: 404 }); }),
    http.post(`${API}/reports/weekly/draft`, () => { posts++; return HttpResponse.json(weeklyReady); }),
  );
  open();
  expect(await screen.findByText("本週尚未產生週報")).toBeInTheDocument();
  await waitFor(() => expect(gets).toBeGreaterThan(0));
  expect(gets).toBeLessThanOrEqual(2);
  expect(posts).toBe(0);
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("L1：按週 GET 真錯誤顯示 ErrorBanner，請求數至多 2", async () => {
  let gets = 0;
  server.use(http.get(`${API}/reports/weekly`, () => {
    gets++;
    return HttpResponse.json({ error: { code: "INTERNAL_ERROR", message: "讀取失敗", details: {} } }, { status: 500 });
  }));
  open();
  expect(await screen.findByRole("alert")).toHaveTextContent("讀取失敗");
  expect(gets).toBeLessThanOrEqual(2);
});

test("沒有週次參數時預設本週週一，並寫入 URL", async () => {
  server.use(http.get(`${API}/reports/weekly`, () => HttpResponse.json({ error: { code: "NOT_FOUND", message: "未產生", details: {} } }, { status: 404 })));
  open("/reports");
  expect(await screen.findByText("本週尚未產生週報")).toBeInTheDocument();
  expect(screen.getByTestId("location")).toHaveTextContent(`week_start=${currentWeekStart()}`);
});

test("AC-48／49：伺服器排除數原樣顯示；對帳不過時夾帶的 draft 不進 DOM", async () => {
  server.use(http.get(`${API}/reports/weekly`, () => HttpResponse.json({ ...weeklyReconciliationFailed, draft: "不可洩露的 AI 初稿" })));
  open();
  expect(await screen.findByText("初稿未通過歷程核對，以下為依目前歷程列出的事件清單")).toBeInTheDocument();
  expect(screen.queryByText("不可洩露的 AI 初稿")).not.toBeInTheDocument();
  expect(screen.getByText(/排除 2 項私人任務/)).toBeInTheDocument();
  expect(screen.getByText("調整範例任務")).toBeInTheDocument();
  expect(screen.getByText(/原訂 2026-11-12/)).toBeInTheDocument();
  expect(screen.getByText(/最新 2026-11-18/)).toBeInTheDocument();
  expect(screen.getByText(/事件後值 2026-11-16/)).toBeInTheDocument();
  expect(screen.getByTestId("location")).toHaveTextContent("report_id=7");
});

test("AC-51／H2：重產降級用本次回應，未儲存人工草稿保留，不立刻 GET 洗掉", async () => {
  const user = userEvent.setup();
  let gets = 0;
  let posts = 0;
  server.use(
    http.get(`${API}/reports/weekly`, () => { gets++; return HttpResponse.json(weeklyReady); }),
    http.post(`${API}/reports/weekly/draft`, () => { posts++; return HttpResponse.json(weeklyUnavailable); }),
  );
  open();
  expect(await screen.findByText("本週完成：範例任務。" )).toBeInTheDocument();
  await user.clear(screen.getByLabelText("人工版"));
  await user.type(screen.getByLabelText("人工版"), "尚未儲存的人工內容");
  await user.click(screen.getByRole("button", { name: "重新產生初稿" }));
  expect(await screen.findByText("AI 暫時無法使用，以下顯示可用內容。")).toBeInTheDocument();
  expect(screen.queryByText("本週完成：範例任務。" )).not.toBeInTheDocument();
  expect(screen.getByLabelText("人工版")).toHaveValue("尚未儲存的人工內容");
  expect(gets).toBe(1);
  expect(posts).toBe(1);
});

test("同週重讀期間隱藏舊 AI，但保留未儲存人工草稿", async () => {
  const user = userEvent.setup();
  let reads = 0;
  let finishRead: ((value: Response) => void) | undefined;
  server.use(http.get(`${API}/reports/weekly`, () => {
    reads++;
    if (reads === 1) return HttpResponse.json(weeklyReady);
    return new Promise<Response>((resolve) => { finishRead = resolve; });
  }));
  const { client } = open();
  await screen.findByText("本週完成：範例任務。");
  await user.type(screen.getByLabelText("人工版"), "新");
  const refetch = client.refetchQueries({ queryKey: ["reports", "weekly", "week", "2026-11-09"] });
  await waitFor(() => expect(reads).toBe(2));
  expect(screen.queryByText("本週完成：範例任務。")).not.toBeInTheDocument();
  expect(screen.getByLabelText("人工版")).toHaveValue("範例人工版：由使用者修改。新");
  finishRead?.(HttpResponse.json(weeklyReady));
  await refetch;
});

test("404 後明確產稿才 POST，成功顯示本次回應且 URL 記 id", async () => {
  const user = userEvent.setup();
  let gets = 0;
  server.use(
    http.get(`${API}/reports/weekly`, () => { gets++; return HttpResponse.json({ error: { code: "NOT_FOUND", message: "未產生", details: {} } }, { status: 404 }); }),
    http.post(`${API}/reports/weekly/draft`, () => HttpResponse.json(weeklyReady)),
  );
  open();
  await screen.findByText("本週尚未產生週報");
  await user.click(screen.getByRole("button", { name: "產生初稿" }));
  expect(await screen.findByText("本週完成：範例任務。")).toBeInTheDocument();
  expect(screen.getByTestId("location")).toHaveTextContent("report_id=7");
  expect(gets).toBe(1);
});

test("PUT manual 只送人工文字，不帶版本；完成後保留回傳值", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(
    http.get(`${API}/reports/weekly`, () => HttpResponse.json(weeklyReady)),
    http.put(`${API}/reports/weekly/7/manual`, async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json({ ...weeklyReady, manual_text: "更新後人工版" });
    }),
  );
  open();
  await screen.findByText("本週完成：範例任務。");
  await user.clear(screen.getByLabelText("人工版"));
  await user.type(screen.getByLabelText("人工版"), "更新後人工版");
  await user.click(screen.getByRole("button", { name: "儲存人工版" }));
  expect(await screen.findByText("已儲存人工版")).toBeInTheDocument();
  expect(bodies).toEqual([{ manual_text: "更新後人工版" }]);
});

test("週日選週換成週一並寫 URL；切週不顯示舊週初稿", async () => {
  const weeks: string[] = [];
  server.use(http.get(`${API}/reports/weekly`, ({ request }) => {
    const week = new URL(request.url).searchParams.get("week_start") ?? "";
    weeks.push(week);
    if (week === "2026-11-16") return HttpResponse.json({ error: { code: "NOT_FOUND", message: "未產生", details: { week_start: week } } }, { status: 404 });
    return HttpResponse.json(weeklyReady);
  }));
  open();
  await screen.findByText("本週完成：範例任務。");
  fireEvent.change(screen.getByLabelText("選擇週次"), { target: { value: "2026-11-22" } });
  expect(await screen.findByText("本週尚未產生週報")).toBeInTheDocument();
  expect(screen.queryByText("本週完成：範例任務。")).not.toBeInTheDocument();
  expect(weeks).toContain("2026-11-16");
  expect(screen.getByTestId("location")).not.toHaveTextContent("report_id=");
});

test("invalid_output 與空 items 走成功退路，人工版仍能編輯", async () => {
  server.use(http.get(`${API}/reports/weekly`, () => HttpResponse.json({ ...weeklyInvalidOutput, items: weeklyEmpty.items })));
  open();
  expect(await screen.findByText("AI 回傳內容未通過檢查，以下顯示可用內容。")).toBeInTheDocument();
  expect(screen.getByText("本週沒有可列的工作項目。")).toBeInTheDocument();
  expect(screen.getByLabelText("人工版")).not.toBeDisabled();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("非週一等 422 顯示錯誤且不自動改值重送", async () => {
  const user = userEvent.setup();
  let posts = 0;
  server.use(
    http.get(`${API}/reports/weekly`, () => HttpResponse.json({ error: { code: "NOT_FOUND", message: "未產生", details: {} } }, { status: 404 })),
    http.post(`${API}/reports/weekly/draft`, () => {
      posts++;
      return HttpResponse.json({ error: { code: "VALIDATION_ERROR", message: "週次必須是週一", details: { fields: ["week_start"] } } }, { status: 422 });
    }),
  );
  open();
  await screen.findByText("本週尚未產生週報");
  await user.click(screen.getByRole("button", { name: "產生初稿" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("週次必須是週一");
  expect(posts).toBe(1);
});

test("人工版 413 顯示本頁文字，保留未儲存輸入", async () => {
  const user = userEvent.setup();
  server.use(
    http.get(`${API}/reports/weekly`, () => HttpResponse.json(weeklyReady)),
    http.put(`${API}/reports/weekly/7/manual`, () => HttpResponse.json({ error: { code: "PAYLOAD_TOO_LARGE", message: "Too long", details: {} } }, { status: 413 })),
  );
  open();
  await screen.findByText("本週完成：範例任務。");
  await user.clear(screen.getByLabelText("人工版"));
  await user.type(screen.getByLabelText("人工版"), "待保存內容");
  await user.click(screen.getByRole("button", { name: "儲存人工版" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("人工版超過 20,000 字");
  expect(screen.getByLabelText("人工版")).toHaveValue("待保存內容");
});

test("切週前有未存人工文字，取消則維持原週", async () => {
  const user = userEvent.setup();
  const ask = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
  server.use(http.get(`${API}/reports/weekly`, () => HttpResponse.json(weeklyReady)));
  open();
  await screen.findByText("本週完成：範例任務。");
  await user.type(screen.getByLabelText("人工版"), "新");
  fireEvent.change(screen.getByLabelText("選擇週次"), { target: { value: "2026-11-22" } });
  expect(screen.getByTestId("location")).toHaveTextContent("week_start=2026-11-09");
  expect(screen.getByLabelText("人工版")).toHaveValue("範例人工版：由使用者修改。新");
  expect(ask).toHaveBeenCalledOnce();
  ask.mockRestore();
});

test("人工版未儲存時，點站內連結離頁先確認；取消則留在週報", async () => {
  const user = userEvent.setup();
  const ask = vi.spyOn(window, "confirm").mockReturnValue(false);
  server.use(http.get(`${API}/reports/weekly`, () => HttpResponse.json(weeklyReady)));
  try {
    open();
    await screen.findByText("本週完成：範例任務。");
    await user.type(screen.getByLabelText("人工版"), "新");
    await user.click(screen.getByRole("link", { name: "離開週報" }));
    expect(ask).toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "週報" })).toBeInTheDocument();
    expect(screen.queryByText("歷程頁")).not.toBeInTheDocument();
  } finally { ask.mockRestore(); }
});

test.each([404, 401])("L1 真實 App 守門：週報 GET %s 不使頁面反覆卸載重送", async (status) => {
  let gets = 0;
  localStorage.setItem("g4.token", "test-token");
  vi.stubGlobal("matchMedia", (media: string) => ({ matches: false, media,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  window.history.replaceState({}, "", "/reports?week_start=2026-11-09");
  server.use(
    http.get(`${API}/settings`, () => HttpResponse.json({ onboarded_at: "2026-11-01T10:00:00+08:00" })),
    http.get(`${API}/reports/weekly`, () => {
      gets++;
      return HttpResponse.json({ error: { code: status === 404 ? "NOT_FOUND" : "UNAUTHORIZED", message: "測試錯誤", details: {} } }, { status });
    }),
  );
  try {
    render(<App />);
    if (status === 404) expect(await screen.findByText("本週尚未產生週報")).toBeInTheDocument();
    else expect(await screen.findByRole("alert")).toHaveTextContent("存取 token 錯誤或未設定。");
    expect(screen.getByRole("heading", { name: "週報" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/reports");
    await waitFor(() => expect(gets).toBeGreaterThan(0));
    expect(gets).toBeLessThanOrEqual(2);
  } finally {
    localStorage.removeItem("g4.token");
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  }
});
