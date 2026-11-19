import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { App } from "../../App";
import { todayFixtures, makeTask } from "../../test/fixtures";
import { API, apiError, renderWithClient, server } from "../../test/server";
import { TodayPage } from "./TodayPage";

function open() {
  return renderWithClient(<MemoryRouter initialEntries={["/today"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <Routes><Route path="/today" element={<TodayPage />} /></Routes>
  </MemoryRouter>);
}

beforeEach(() => server.use(
  http.get(`${API}/meta/today`, () => HttpResponse.json(todayFixtures.today)),
  http.get(`${API}/tasks`, () => HttpResponse.json(todayFixtures.tasks)),
  http.get(`${API}/feedback/pending`, () => HttpResponse.json(todayFixtures.pending)),
));

test("US-14：依伺服器今天查 due_before，分逾期與今日並排除 done", async () => {
  const searches: string[] = [];
  server.use(http.get(`${API}/tasks`, ({ request }) => {
    const url = new URL(request.url);
    searches.push(url.search);
    const boundary = url.searchParams.get("due_before");
    const items = todayFixtures.tasks.items.filter(task => !boundary || task.latest_due < boundary);
    return HttpResponse.json({ items, total: items.length });
  }));
  open();
  const overdue = await screen.findByRole("region", { name: "逾期任務" });
  expect(within(overdue).getByRole("link", { name: "逾期範例" })).toBeInTheDocument();
  const today = screen.getByRole("region", { name: "今日任務" });
  expect(within(today).getByRole("link", { name: "今日範例" })).toBeInTheDocument();
  expect(within(overdue).queryByText("已完成範例")).not.toBeInTheDocument();
  expect(within(today).queryByText("已完成範例")).not.toBeInTheDocument();
  expect(searches[0]).toContain("due_before=2026-11-20");
  expect(searches[0]).not.toContain("status=");
  expect(within(overdue).getByText(/狀態：待辦/)).toBeInTheDocument();
  expect(within(today).getByText(/狀態：進行中/)).toBeInTheDocument();
  expect(within(overdue).getByRole("heading", { name: "逾期", level: 3 })).toBeInTheDocument();
  expect(within(today).getByRole("heading", { name: "今日", level: 3 })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "補填已完成範例回報" })).toHaveAttribute("href", "/tasks/103/feedback");
  expect(screen.getByText(/逾期 2 天/)).toBeInTheDocument();
});

test.each([["2026-12-31", "2027-01-01"], ["2028-02-29", "2028-03-01"]])(
  "伺服器今天 %s 的嚴格小於邊界為 %s", async (serverToday, expectedBoundary) => {
    const searches: string[] = [];
    server.use(http.get(`${API}/meta/today`, () => HttpResponse.json({ today: serverToday })),
      http.get(`${API}/tasks`, ({ request }) => {
        searches.push(new URL(request.url).search);
        return HttpResponse.json({ items: [], total: 0 });
      }));
    open();
    await screen.findByText("今日沒有待處理任務。");
    expect(searches[0]).toContain(`due_before=${expectedBoundary}`);
  },
);

test("回到今日後只顯示一次儲存成功訊息，隨即清除 history state", async () => {
  function StateProbe() {
    const location = useLocation();
    return <output data-testid="history-state">{JSON.stringify(location.state)}</output>;
  }
  renderWithClient(<MemoryRouter initialEntries={[{ pathname: "/today", state: { feedbackSaved: todayFixtures.feedback } }]}
    future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <TodayPage /><StateProbe />
  </MemoryRouter>);
  expect(screen.getByText(/完成回報已儲存/)).toBeInTheDocument();
  await waitFor(() => expect(screen.getByTestId("history-state").textContent).toBe("null"));
});

test("今日任務與待補清單各自有 loading、error、empty，不把錯誤當空清單", async () => {
  let release!: () => void;
  const hold = new Promise<void>(resolve => { release = resolve; });
  server.use(http.get(`${API}/tasks`, async () => { await hold; return apiError(404, "NOT_FOUND"); }),
    http.get(`${API}/feedback/pending`, () => HttpResponse.json(todayFixtures.emptyPending)));
  open();
  expect(await screen.findByText("沒有待補完成回報。")).toBeInTheDocument();
  expect(screen.getByText("載入今日任務中…")).toBeInTheDocument();
  release();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByText("今日沒有待處理任務。")).not.toBeInTheDocument();
});

test("待補清單錯誤不遮掉今日任務；任務空時顯示獨立空狀態", async () => {
  server.use(http.get(`${API}/tasks`, () => HttpResponse.json({ items: [], total: 0 })),
    http.get(`${API}/feedback/pending`, () => apiError(404, "NOT_FOUND")));
  open();
  expect(await screen.findByText("今日沒有待處理任務。")).toBeInTheDocument();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByText("沒有待補完成回報。")).not.toBeInTheDocument();
});

test("伺服器今天讀取失敗時不查任務、不改用瀏覽器時鐘", async () => {
  let tasks = 0;
  server.use(http.get(`${API}/meta/today`, () => apiError(404, "NOT_FOUND")),
    http.get(`${API}/tasks`, () => { tasks++; return HttpResponse.json(todayFixtures.tasks); }));
  open();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(tasks).toBe(0);
  expect(screen.queryByText("今日沒有待處理任務。")).not.toBeInTheDocument();
});

test("FR-FBK-01／05：完成只送 expected_version、省略 done_date；稍後補不送 PUT 且任務維持 done", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  let feedbackPuts = 0;
  let completed = false;
  server.use(http.get(`${API}/tasks`, () => HttpResponse.json(completed
    ? { items: [todayFixtures.completed.task], total: 1 } : todayFixtures.tasks)),
  http.get(`${API}/feedback/pending`, () => HttpResponse.json(completed
    ? { ...todayFixtures.pending, items: [{ ...todayFixtures.pending.items[0], task_id: 101, title: "逾期範例" }] }
    : todayFixtures.pending)),
  http.post(`${API}/tasks/101/complete`, async ({ request }) => {
    bodies.push(await request.json()); completed = true;
    return HttpResponse.json(todayFixtures.completed);
  }),
  http.put(`${API}/tasks/101/feedback`, () => { feedbackPuts++; return HttpResponse.json({}); }));
  open();
  await user.click(await screen.findByRole("button", { name: "完成逾期範例" }));
  expect(await screen.findByText("逾期範例已完成。")).toBeInTheDocument();
  expect(bodies).toEqual([{ expected_version: 3 }]);
  expect(screen.getByRole("link", { name: "填寫完成回報" })).toHaveAttribute("href", "/tasks/101/feedback");
  await user.click(screen.getByRole("button", { name: "稍後補" }));
  expect(feedbackPuts).toBe(0);
  expect(await screen.findByRole("link", { name: "補填逾期範例回報" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "完成逾期範例" })).not.toBeInTheDocument();
});

test("完成日補記須明選日期；未展開時不預填瀏覽器今天", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(http.post(`${API}/tasks/101/complete`, async ({ request }) => {
    bodies.push(await request.json()); return HttpResponse.json({ ...todayFixtures.completed, feedback_required: false });
  }));
  open();
  await user.click(await screen.findByRole("button", { name: "補記逾期範例完成日" }));
  const date = screen.getByLabelText("完成日");
  expect(date).toHaveValue("");
  await user.type(date, "2026-11-17");
  await user.click(screen.getByRole("button", { name: "完成逾期範例" }));
  await waitFor(() => expect(bodies).toEqual([{ expected_version: 3, done_date: "2026-11-17" }]));
  expect(screen.queryByRole("link", { name: "填寫完成回報" })).not.toBeInTheDocument();
});

test("STALE_VERSION 重讀任務清單但不重送完成，使用者須重新操作", async () => {
  const user = userEvent.setup();
  let gets = 0;
  let posts = 0;
  server.use(http.get(`${API}/tasks`, () => {
    gets++;
    return HttpResponse.json(gets === 1 ? todayFixtures.tasks : { items: [makeTask({
      id: 101, title: "逾期範例", latest_due: "2026-11-18", version: 4,
    })], total: 1 });
  }), http.post(`${API}/tasks/101/complete`, () => { posts++; return apiError(409, "STALE_VERSION"); }));
  open();
  await user.click(await screen.findByRole("button", { name: "完成逾期範例" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  await waitFor(() => expect(gets).toBeGreaterThanOrEqual(2));
  expect(posts).toBe(1);
});

test.each([404, 401])("L1：真實守門下今日任務與待補 GET %s 各不超過兩次", async status => {
  let tasks = 0; let pending = 0;
  localStorage.setItem("g4.token", "test-token");
  vi.stubGlobal("matchMedia", (media: string) => ({ matches: false, media,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  window.history.replaceState({}, "", "/today");
  server.use(http.get(`${API}/tasks`, () => { tasks++; return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED"); }),
    http.get(`${API}/feedback/pending`, () => { pending++; return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED"); }));
  try {
    render(<App />);
    expect((await screen.findAllByRole("alert")).length).toBeGreaterThan(0);
    await waitFor(() => expect(tasks).toBeGreaterThan(0));
    await waitFor(() => expect(pending).toBeGreaterThan(0));
    expect(tasks).toBeLessThanOrEqual(2);
    expect(pending).toBeLessThanOrEqual(2);
  } finally { localStorage.removeItem("g4.token"); vi.unstubAllGlobals(); window.history.replaceState({}, "", "/"); }
});
