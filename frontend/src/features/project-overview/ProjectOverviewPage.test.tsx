import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { App } from "../../App";
import { keys } from "../../api/queryKeys";
import { dueFixtures, makeSerializedEvent, makeTask, overviewFixtures } from "../../test/fixtures";
import { API, apiError, renderWithClient, server } from "../../test/server";
import { ProjectOverviewPage } from "./ProjectOverviewPage";

function open(path = "/projects/1") {
  return renderWithClient(<MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <Routes><Route path="/projects/:projectId" element={<ProjectOverviewPage />} /></Routes>
  </MemoryRouter>);
}

test("AC-34：摘要照伺服器值，候選與正式任務分離；甘特吃整包 GanttOut", async () => {
  const gantt = { ...overviewFixtures.gantt, summary: { done: 7, total: 20, delayed: 5, open_candidates: 2 } };
  server.use(http.get(`${API}/projects/1/gantt`, () => HttpResponse.json(gantt)));
  open();
  expect(await screen.findByRole("heading", { name: "範例專案" })).toBeInTheDocument();
  expect(screen.getByText("已完成 7／20")).toBeInTheDocument();
  expect(screen.getByText("已延期 5")).toBeInTheDocument();
  expect(screen.getByText("已對應本專案的待確認候選：2")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "專案甘特圖" })).toBeInTheDocument();
  expect(screen.queryByText(/完成率|%/)).not.toBeInTheDocument();
});

test("FR-PRJ-05：任務表欄序與甘特同源，原訂唯讀，完成列不提供改期", async () => {
  open();
  await screen.findByRole("link", { name: "範例任務甲" });
  expect(screen.getAllByRole("columnheader").map(node => node.textContent)).toEqual([
    "任務", "負責人", "狀態", "開始", "原訂", "最新預計", "與原訂差距", "日期操作",
  ]);
  const row = screen.getByRole("row", { name: /範例任務甲/ });
  expect(within(row).getByText("2026-11-18")).toBeInTheDocument();
  expect(within(row).getByText("2026-11-20")).toBeInTheDocument();
  expect(within(row).getByText("已封鎖")).toBeInTheDocument();
  expect(within(row).getByText("2 天")).toBeInTheDocument();
  expect(within(screen.getByRole("row", { name: /範例任務乙/ })).getByText("-5 天")).toBeInTheDocument();
  expect(within(row).getByRole("link", { name: "範例任務甲" })).toHaveAttribute("href", "/tasks/101");
  expect(within(screen.getByRole("row", { name: /範例任務丙/ })).queryByRole("button", { name: /改預計日/ })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "專案歷程" })).toHaveAttribute("href", "/projects/1/history");
  expect(screen.getByRole("link", { name: "整批順延" })).toHaveAttribute("href", "/projects/1/bulk-shift");
});

test("空專案仍顯示候選數和甘特空圖，不誤判為錯誤", async () => {
  server.use(http.get(`${API}/projects/1/gantt`, () => HttpResponse.json(overviewFixtures.empty)));
  open();
  expect(await screen.findByText("此專案尚無任務。")).toBeInTheDocument();
  expect(screen.getByText("已對應本專案的待確認候選：2")).toBeInTheDocument();
  expect(screen.getByText("此專案尚無可繪製的時間資料")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("NOT_FOUND 與空專案分離，loading 時不先顯示零計數", async () => {
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  server.use(http.get(`${API}/projects/1/gantt`, async () => { await pending; return apiError(404, "NOT_FOUND"); }));
  open();
  expect(screen.getByText("載入專案現況中…")).toHaveAttribute("role", "status");
  expect(screen.queryByText("已完成 0／0")).not.toBeInTheDocument();
  release();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByText("此專案尚無任務。")).not.toBeInTheDocument();
});

test("無效專案 id 不送出專案或甘特請求", () => {
  let calls = 0;
  server.use(http.get(`${API}/projects/:id`, () => { calls++; return HttpResponse.json(overviewFixtures.project); }),
    http.get(`${API}/projects/:id/gantt`, () => { calls++; return HttpResponse.json(overviewFixtures.gantt); }));
  open("/projects/invalid");
  expect(screen.getByRole("alert")).toHaveTextContent("無效的專案編號");
  expect(calls).toBe(0);
});

test("改期只展開既有面板，日期不預填；取消不使甘特重讀", async () => {
  const user = userEvent.setup();
  let ganttGets = 0;
  server.use(http.get(`${API}/projects/1/gantt`, () => { ganttGets++; return HttpResponse.json(overviewFixtures.gantt); }),
    http.get(`${API}/tasks/101`, () => HttpResponse.json({ task: makeTask({ id: 101, project_id: 1, title: "範例任務甲", version: 4 }) })));
  const { client } = open();
  await screen.findByRole("button", { name: "改預計日：範例任務甲" });
  await user.click(screen.getByRole("button", { name: "改預計日：範例任務甲" }));
  expect(await screen.findByLabelText("新的預計完成日")).toHaveValue("");
  expect(client.getQueryData(keys.gantt(1))).toEqual(overviewFixtures.gantt);
  expect(ganttGets).toBe(1);
  await user.click(screen.getByRole("button", { name: "關閉" }));
  expect(ganttGets).toBe(1);
});

test("改期成功只由既有面板寫入，並使本專案甘特失效重讀", async () => {
  const user = userEvent.setup();
  let ganttGets = 0;
  server.use(
    http.get(`${API}/projects/1/gantt`, () => { ganttGets++; return HttpResponse.json(overviewFixtures.gantt); }),
    http.get(`${API}/tasks/101`, () => HttpResponse.json({ task: makeTask({ id: 101, owner: "範例協作者", version: 4 }) })),
    http.post(`${API}/tasks/101/adjust-due`, () => HttpResponse.json({
      ...dueFixtures.success.response,
      task: makeTask({ id: 101, owner: "範例協作者", latest_due: "2026-11-21", version: 5 }),
      event: makeSerializedEvent({ id: 210, task_id: 101, kind: "due" }),
    })),
  );
  open();
  await screen.findByRole("button", { name: "改預計日：範例任務甲" });
  await user.click(screen.getByRole("button", { name: "改預計日：範例任務甲" }));
  const input = await screen.findByLabelText("新的預計完成日");
  await user.type(input, "2026-11-21");
  await screen.findByRole("option", { name: "等對方或客戶回覆（外部）" });
  await user.selectOptions(screen.getByLabelText("原因"), "wait_external");
  await user.click(screen.getByRole("button", { name: "確認調整" }));
  await waitFor(() => expect(ganttGets).toBe(2));
  expect(screen.queryByLabelText("新的預計完成日")).not.toBeInTheDocument();
});

test.each([404, 401])("L1：真實 App 守門下 Gantt GET %s 請求數 ≤2", async status => {
  let calls = 0;
  localStorage.setItem("g4.token", "test-token");
  vi.stubGlobal("matchMedia", (media: string) => ({ matches: false, media,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  window.history.replaceState({}, "", "/projects/1");
  server.use(http.get(`${API}/projects/1/gantt`, () => { calls++; return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED"); }));
  try {
    render(<App />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await waitFor(() => expect(calls).toBeGreaterThan(0));
    expect(calls).toBeLessThanOrEqual(2);
  } finally { localStorage.removeItem("g4.token"); vi.unstubAllGlobals(); window.history.replaceState({}, "", "/"); }
});
