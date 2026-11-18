import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { keys } from "../../api/queryKeys";
import { OnboardingGate } from "../settings/OnboardingGate";
import { adjustStartFixtures, historyFixtures, makeSerializedEvent, makeTask } from "../../test/fixtures";
import { API, renderWithClient, server } from "../../test/server";
import { TaskDetailPage } from "./TaskDetailPage";

function open(withGate = false) {
  return renderWithClient(<MemoryRouter initialEntries={["/tasks/4"]}>
    {withGate ? <OnboardingGate><Routes><Route path="/tasks/:taskId" element={<TaskDetailPage />} /></Routes></OnboardingGate>
      : <Routes><Route path="/tasks/:taskId" element={<TaskDetailPage />} /></Routes>}
  </MemoryRouter>);
}

test("AC-27／29：共享 task key 存完整 TaskOut，歷程另讀 /events 並保留事件快照", async () => {
  const queries: string[] = [];
  server.use(http.get(`${API}/events`, ({ request }) => {
    queries.push(new URL(request.url).search);
    return HttpResponse.json(historyFixtures.marked);
  }));
  const { client } = open();
  expect(await screen.findByRole("heading", { name: "確認驗收條件" })).toBeInTheDocument();
  expect(await screen.findByText("舊任務名稱")).toBeInTheDocument();
  expect(queries[0]).toContain("task_id=4");
  expect(queries[0]).toContain("limit=100");
  expect(client.getQueryData(keys.task(4))).toEqual(makeTask());
  expect(screen.queryByText("尚未回報")).not.toBeInTheDocument();
});

test("AC-08／09／10：註記不預選，稍後只關閉，確認才 POST 並失效全部統計日期", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(
    http.get(`${API}/events`, () => HttpResponse.json(historyFixtures.unmarked)),
    http.post(`${API}/events/202/annotations`, async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json({ event: makeSerializedEvent({ kind: "annotation", ref_event_id: 202, mark: "better" }), effective_mark: "better" }, { status: 201 });
    }),
  );
  const { client } = open();
  client.setQueryData(keys.timeManagement({ from: "2026-11-01" }), { judgement: null });
  await user.click(await screen.findByRole("button", { name: "補註記" }));
  expect(screen.getByRole("radio", { name: "變好" })).not.toBeChecked();
  expect(screen.getByRole("radio", { name: "變差" })).not.toBeChecked();
  await user.click(screen.getByRole("radio", { name: "稍後註記" }));
  expect(screen.queryByRole("radio", { name: "變好" })).not.toBeInTheDocument();
  expect(bodies).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "補註記" }));
  await user.click(screen.getByRole("radio", { name: "變好" }));
  await user.type(screen.getByLabelText("註記備註"), "範例補充");
  await user.click(screen.getByRole("button", { name: "儲存註記" }));
  await waitFor(() => expect(bodies).toEqual([{ mark: "better", reason: null, note: "範例補充" }]));
  await waitFor(() => expect(client.getQueryState(keys.timeManagement({ from: "2026-11-01" }))?.isInvalidated).toBe(true));
});

test("歷程查詢分頁使用 offset，另一頁不沿用前頁資料", async () => {
  const user = userEvent.setup();
  const offsets: string[] = [];
  server.use(http.get(`${API}/events`, ({ request }) => {
    const offset = new URL(request.url).searchParams.get("offset") ?? "";
    offsets.push(offset);
    return HttpResponse.json(offset === "100"
      ? { items: [{ ...historyFixtures.marked.items[0], id: 999, task_title: "下一頁任務" }], total: 101 }
      : { ...historyFixtures.marked, total: 101 });
  }));
  open();
  await screen.findByText("舊任務名稱");
  await user.click(screen.getByRole("button", { name: "下一頁" }));
  expect(await screen.findByText("下一頁任務")).toBeInTheDocument();
  expect(screen.queryByText("舊任務名稱")).not.toBeInTheDocument();
  expect(offsets).toContain("100");
});

test("成功且歷程 items 空才顯示空狀態", async () => {
  server.use(http.get(`${API}/events`, () => HttpResponse.json(historyFixtures.empty)));
  open();
  expect(await screen.findByText("本任務目前沒有符合條件的歷程。")).toBeInTheDocument();
});

test("AC-62：開始日初值空白，只送 new_start＋版本；警告仍成功且期限不變", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(http.post(`${API}/tasks/4/adjust-start`, async ({ request }) => {
    bodies.push(await request.json());
    return HttpResponse.json({ task: makeTask({ start: "2026-11-21", version: 2 }),
      event: makeSerializedEvent({ kind: "task", field: "start_date", to_value: "2026-11-21" }),
      warnings: adjustStartFixtures.afterDue.response.warnings });
  }));
  const { client } = open();
  await user.click(await screen.findByRole("button", { name: "調整開始日" }));
  expect(screen.getByLabelText("新的開始日")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("新的開始日"), { target: { value: "2026-11-21" } });
  await user.click(screen.getByRole("button", { name: "確認開始日" }));
  expect(await screen.findByText(/開始日晚於最新預計日/)).toBeInTheDocument();
  expect(bodies).toEqual([{ new_start: "2026-11-21", expected_version: 1 }]);
  expect(client.getQueryData(keys.task(4))).toMatchObject({ start: "2026-11-21", orig_due: "2026-11-18", latest_due: "2026-11-18" });
});

test("基準外層只在既有 task 的 orig_due 後續變動時失效 events/gantt/projects", async () => {
  const { client } = open();
  await screen.findByRole("heading", { name: "確認驗收條件" });
  client.setQueryData(keys.gantt(1), { rows: [] });
  client.setQueryData(keys.project(1), { id: 1 });
  await screen.findByText("舊任務名稱");
  expect(client.getQueryState(keys.gantt(1))?.isInvalidated).toBe(false);
  act(() => client.setQueryData(keys.task(4), makeTask({ latest_due: "2026-11-20" })));
  expect(client.getQueryState(keys.gantt(1))?.isInvalidated).toBe(false);
  act(() => client.setQueryData(keys.task(4), makeTask({ orig_due: "2026-11-19" })));
  await waitFor(() => expect(client.getQueryState(keys.gantt(1))?.isInvalidated).toBe(true));
  expect(client.getQueryState(keys.project(1))?.isInvalidated).toBe(true);
});

test.each([404, 401])("L1：真實守門下 task GET %s 至多重送兩次", async status => {
  let gets = 0;
  server.use(
    http.get(`${API}/settings`, () => HttpResponse.json({ onboarded_at: "2026-11-01T10:00:00+08:00" })),
    http.get(`${API}/tasks/4`, () => {
      gets++;
      return HttpResponse.json({ error: { code: status === 404 ? "NOT_FOUND" : "UNAUTHORIZED", message: "讀取失敗", details: {} } }, { status });
    }),
  );
  open(true);
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  await waitFor(() => expect(gets).toBeGreaterThan(0));
  expect(gets).toBeLessThanOrEqual(2);
});

test.each([404, 401])("L1：真實守門下 events GET %s 至多重送兩次，任務摘要仍可看", async status => {
  let gets = 0;
  server.use(
    http.get(`${API}/settings`, () => HttpResponse.json({ onboarded_at: "2026-11-01T10:00:00+08:00" })),
    http.get(`${API}/events`, () => {
      gets++;
      return HttpResponse.json({ error: { code: status === 404 ? "NOT_FOUND" : "UNAUTHORIZED", message: "歷程讀取失敗", details: {} } }, { status });
    }),
  );
  open(true);
  expect(await screen.findByRole("heading", { name: "確認驗收條件" })).toBeInTheDocument();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  await waitFor(() => expect(gets).toBeGreaterThan(0));
  expect(gets).toBeLessThanOrEqual(2);
});
