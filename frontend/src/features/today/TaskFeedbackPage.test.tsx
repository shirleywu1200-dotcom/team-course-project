import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { App } from "../../App";
import { keys } from "../../api/queryKeys";
import { makeTask, todayFixtures } from "../../test/fixtures";
import { API, RUBRIC_V0, apiError, renderWithClient, server } from "../../test/server";
import { TaskFeedbackPage } from "./TaskFeedbackPage";
import { TodayPage } from "./TodayPage";

const doneTask = makeTask({ id: 103, title: "已完成範例", status: "done", done_date: "2026-11-19", rubric_id: 1 });
function open(path = "/tasks/103/feedback") {
  return renderWithClient(<MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <Routes><Route path="/tasks/:taskId/feedback" element={<TaskFeedbackPage />} />
      <Route path="/today" element={<TodayPage />} /></Routes>
  </MemoryRouter>);
}

beforeEach(() => server.use(
  http.get(`${API}/tasks/103`, () => HttpResponse.json({ task: doneTask, events: [] })),
  http.get(`${API}/tasks/103/feedback`, () => apiError(404, "NOT_FOUND")),
));

test("AC-43：星數、精力與選填投入初值空，事前星數僅展示，缺必填不送 PUT", async () => {
  let puts = 0;
  server.use(http.put(`${API}/tasks/103/feedback`, () => { puts++; return HttpResponse.json(todayFixtures.savedFeedback, { status: 201 }); }));
  open();
  expect(await screen.findByText("事前預設星數：3")).toBeInTheDocument();
  expect(screen.getByText("事前量表版本：1")).toBeInTheDocument();
  expect(await screen.findByLabelText("實際達成星數")).toHaveValue("");
  expect(screen.getByLabelText("自評精力")).toHaveValue("");
  expect(screen.getByLabelText("投入相對預期")).toHaveValue("");
  expect(screen.getByRole("button", { name: "儲存完成回報" })).toBeDisabled();
  expect(puts).toBe(0);
});

test("AC-44：只送使用者明選值，overdue_days 與 goal_id 不送；成功顯示伺服器逾期值", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  let pendingGets = 0;
  server.use(http.put(`${API}/tasks/103/feedback`, async ({ request }) => {
    bodies.push(await request.json()); return HttpResponse.json(todayFixtures.savedFeedback, { status: 201 });
  }), http.get(`${API}/feedback/pending`, () => {
    pendingGets++; return HttpResponse.json(todayFixtures.emptyPending);
  }));
  const { client } = open();
  client.setQueryData(keys.feedbackPending(), todayFixtures.pending);
  await user.selectOptions(await screen.findByLabelText("實際達成星數"), "5");
  await user.selectOptions(screen.getByLabelText("自評精力"), "low");
  await user.selectOptions(screen.getByLabelText("投入相對預期"), "less");
  await user.click(screen.getByRole("button", { name: "儲存完成回報" }));
  await waitFor(() => expect(bodies).toEqual([{
    actual_stars: 5, energy: "low", invest_vs_expected: "less", rubric_id: 1,
  }]));
  expect(await screen.findByRole("heading", { name: "今日", level: 1 })).toBeInTheDocument();
  expect(screen.getByText("完成回報已儲存。伺服器計算逾期天數：7 天")).toBeInTheDocument();
  expect(await screen.findByText("沒有待補完成回報。")).toBeInTheDocument();
  expect(pendingGets).toBeGreaterThanOrEqual(1);
  expect(client.getQueryData(keys.feedback(103))).toEqual(todayFixtures.savedFeedback.feedback);
});

test("AC-45：從 active=true 擷取最大 version 的 id；TaskOut 量表可空，填寫中換版仍送開啟時 id", async () => {
  const user = userEvent.setup();
  let rubricGets = 0;
  const bodies: unknown[] = [];
  server.use(http.get(`${API}/tasks/103`, () => HttpResponse.json({ task: { ...doneTask, rubric_id: null }, events: [] })),
    http.get(`${API}/rubrics`, ({ request }) => {
      expect(new URL(request.url).searchParams.get("active")).toBe("true");
      rubricGets++;
      return HttpResponse.json(rubricGets === 1
        ? { items: [{ ...RUBRIC_V0, id: 7, version: 2 }, { ...RUBRIC_V0, id: 8, version: 3 }], total: 2 }
        : { items: [{ ...RUBRIC_V0, id: 9, version: 4 }], total: 1 });
    }),
    http.put(`${API}/tasks/103/feedback`, async ({ request }) => {
      bodies.push(await request.json()); return HttpResponse.json(todayFixtures.savedFeedback, { status: 201 });
    }));
  const { client } = open();
  await user.selectOptions(await screen.findByLabelText("實際達成星數"), "4");
  expect(client.getQueryData(keys.activeRubric)).toMatchObject({ id: 8, version: 3 });
  await client.invalidateQueries({ queryKey: keys.activeRubric });
  await waitFor(() => expect(rubricGets).toBe(2));
  await user.selectOptions(screen.getByLabelText("自評精力"), "mid");
  await user.click(screen.getByRole("button", { name: "儲存完成回報" }));
  await waitFor(() => expect(bodies).toEqual([{ actual_stars: 4, energy: "mid", rubric_id: 8 }]));
});

test("已有回報只顯示唯讀目前回報與修改未開放，不提供第二次 PUT", async () => {
  let puts = 0;
  server.use(http.get(`${API}/tasks/103/feedback`, () => HttpResponse.json(todayFixtures.feedback)),
    http.put(`${API}/tasks/103/feedback`, () => { puts++; return apiError(409, "FEEDBACK_EXISTS"); }));
  open();
  const card = await screen.findByRole("region", { name: "目前回報" });
  expect(within(card).getByText("逾期天數").nextElementSibling).toHaveTextContent("2 天");
  expect(screen.getByText("修改功能尚未開放")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "儲存完成回報" })).not.toBeInTheDocument();
  expect(puts).toBe(0);
  expect(within(card).getByText("2026-11-19 10:00:00 +08:00")).toBeInTheDocument();
});

test("FEEDBACK_EXISTS：另一分頁先存後重讀目前回報，切換唯讀卡", async () => {
  const user = userEvent.setup();
  let feedbackGets = 0;
  server.use(http.get(`${API}/tasks/103/feedback`, () => {
    feedbackGets++;
    return feedbackGets === 1 ? apiError(404, "NOT_FOUND") : HttpResponse.json(todayFixtures.feedback);
  }), http.put(`${API}/tasks/103/feedback`, () => apiError(409, "FEEDBACK_EXISTS")));
  open();
  await user.selectOptions(await screen.findByLabelText("實際達成星數"), "4");
  await user.selectOptions(screen.getByLabelText("自評精力"), "mid");
  await user.click(screen.getByRole("button", { name: "儲存完成回報" }));
  expect(await screen.findByRole("region", { name: "目前回報" })).toBeInTheDocument();
  expect(feedbackGets).toBeGreaterThanOrEqual(2);
  expect(screen.queryByRole("button", { name: "儲存完成回報" })).not.toBeInTheDocument();
});

test("事前星數來源顯示繁中，不直接露出原始代碼", async () => {
  open();
  expect(await screen.findByText("星數來源：自行設定")).toBeInTheDocument();
  expect(screen.queryByText("星數來源：self")).not.toBeInTheDocument();
});

test("稍後補只返回今日頁，不送空白 PUT、不改已完成任務", async () => {
  let puts = 0;
  server.use(http.put(`${API}/tasks/103/feedback`, () => { puts++; return HttpResponse.json({}); }));
  const user = userEvent.setup();
  open();
  await user.click(await screen.findByRole("button", { name: "稍後補" }));
  expect(await screen.findByRole("heading", { name: "今日", level: 1 })).toBeInTheDocument();
  expect(puts).toBe(0);
});

test("非 done 任務不能儲存回報", async () => {
  server.use(http.get(`${API}/tasks/103`, () => HttpResponse.json({ task: { ...doneTask, status: "todo" }, events: [] })));
  open();
  expect(await screen.findByText("任務尚未完成，不能填寫完成回報。")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "儲存完成回報" })).not.toBeInTheDocument();
});

test("後端 422 保留選擇並顯示錯誤", async () => {
  const user = userEvent.setup();
  server.use(http.put(`${API}/tasks/103/feedback`, () => apiError(422, "VALIDATION_ERROR")));
  open();
  await user.selectOptions(await screen.findByLabelText("實際達成星數"), "4");
  const energy = screen.getByLabelText("自評精力");
  await user.selectOptions(energy, "mid");
  await user.click(screen.getByRole("button", { name: "儲存完成回報" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(energy).toHaveValue("mid");
});

test("任務載入中不顯示可送表單，讀目前回報的真錯誤不誤認未填", async () => {
  let release!: () => void;
  const hold = new Promise<void>(resolve => { release = resolve; });
  server.use(http.get(`${API}/tasks/103`, async () => { await hold; return HttpResponse.json({ task: doneTask, events: [] }); }),
    http.get(`${API}/tasks/103/feedback`, () => apiError(401, "UNAUTHORIZED")));
  open();
  expect(screen.getByText("載入任務中…")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "儲存完成回報" })).not.toBeInTheDocument();
  release();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "儲存完成回報" })).not.toBeInTheDocument();
});

test("目前有效量表不存在或讀取失敗時，不顯示可送出的空回報", async () => {
  server.use(http.get(`${API}/rubrics`, () => HttpResponse.json({ items: [], total: 0 })));
  const empty = open();
  expect(await screen.findByRole("alert")).toHaveTextContent("目前沒有可用的量表版本");
  expect(screen.queryByRole("button", { name: "儲存完成回報" })).not.toBeInTheDocument();
  empty.unmount();

  server.use(http.get(`${API}/rubrics`, () => apiError(401, "UNAUTHORIZED")));
  open();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "儲存完成回報" })).not.toBeInTheDocument();
});

test.each([404, 401])("L1：真實守門下讀目前回報 GET %s 請求數 ≤2", async status => {
  let calls = 0;
  localStorage.setItem("g4.token", "test-token");
  vi.stubGlobal("matchMedia", (media: string) => ({ matches: false, media,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  window.history.replaceState({}, "", "/tasks/103/feedback");
  server.use(http.get(`${API}/tasks/103/feedback`, () => { calls++; return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED"); }));
  try {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "完成回報" })).toBeInTheDocument();
    await waitFor(() => expect(calls).toBeGreaterThan(0));
    expect(calls).toBeLessThanOrEqual(2);
  } finally { localStorage.removeItem("g4.token"); vi.unstubAllGlobals(); window.history.replaceState({}, "", "/"); }
});
