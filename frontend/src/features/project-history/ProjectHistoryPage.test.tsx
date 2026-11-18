import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { App } from "../../App";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { historyFixtures, historyProjectFixture, makeTask } from "../../test/fixtures";
import { API, apiError, renderWithClient, server } from "../../test/server";
import { ProjectHistoryPage } from "./ProjectHistoryPage";

const project = { id: 1, name: "範例專案", scope: "work", audience: "none", line_group_id: null,
  created_at: "2026-11-01T09:00:00+08:00", updated_at: "2026-11-02T09:00:00+08:00", archived_at: null,
} satisfies components["schemas"]["ProjectOut"];

function open(path = "/history") {
  return renderWithClient(<MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <Routes><Route path="/history" element={<ProjectHistoryPage />} />
      <Route path="/projects/:projectId/history" element={<ProjectHistoryPage />} />
      <Route path="/tasks/:taskId" element={<p>任務詳情</p>} /></Routes>
  </MemoryRouter>);
}

test("AC-27：全域專案含封存、單點字串 none、組合篩選只在套用後查", async () => {
  const user = userEvent.setup();
  const calls: URL[] = [];
  server.use(
    http.get(`${API}/projects`, ({ request }) => {
      expect(new URL(request.url).searchParams.get("include_archived")).toBe("true");
      return HttpResponse.json({ items: [project], total: 1 });
    }),
    http.get(`${API}/events`, ({ request }) => { calls.push(new URL(request.url)); return HttpResponse.json(historyFixtures.marked); }),
  );
  open();
  await screen.findByText("舊任務名稱");
  await user.selectOptions(screen.getByRole("combobox", { name: "專案" }), "none");
  await user.selectOptions(screen.getByRole("combobox", { name: "類型" }), "due");
  expect(calls).toHaveLength(1);
  await user.click(screen.getByRole("button", { name: "套用" }));
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls[1].searchParams.get("project_id")).toBe("none");
  expect(calls[1].searchParams.get("kind")).toBe("due");
  expect(screen.getByText("符合 1 筆歷程")).toBeInTheDocument();
});

test("固定專案與全域指定相同條件使用等價 key；路徑限制不被 URL 覆蓋", async () => {
  server.use(http.get(`${API}/projects/1`, () => HttpResponse.json(historyProjectFixture)));
  const { client } = open("/projects/1/history?project_id=none&kind=due");
  expect(await screen.findByRole("heading", { name: "範例專案歷程" })).toBeInTheDocument();
  expect(screen.queryByRole("combobox", { name: "專案" })).not.toBeInTheDocument();
  await screen.findByText("舊任務名稱");
  expect(client.getQueryData(keys.events({ project_id: "1", kind: "due" }))).toEqual(historyFixtures.marked);
});

test("任務下拉用 TaskListOut；換專案清任務，日期與批次按套用才查", async () => {
  const user = userEvent.setup();
  const calls: URL[] = [];
  server.use(
    http.get(`${API}/projects`, () => HttpResponse.json({ items: [project], total: 1 })),
    http.get(`${API}/tasks`, () => HttpResponse.json({ items: [makeTask()], total: 1 })),
    http.get(`${API}/events`, ({ request }) => { calls.push(new URL(request.url)); return HttpResponse.json(historyFixtures.marked); }),
  );
  open("/history?project_id=1&task_id=4");
  await screen.findByText("舊任務名稱");
  expect(screen.getByRole("combobox", { name: "任務" })).toHaveValue("4");
  await user.selectOptions(screen.getByRole("combobox", { name: "專案" }), "none");
  expect(screen.getByRole("combobox", { name: "任務" })).toHaveValue("");
  await user.type(screen.getByRole("spinbutton", { name: "批次編號" }), "31");
  await user.type(screen.getByLabelText("起日"), "2026-11-01");
  expect(calls).toHaveLength(1);
  await user.click(screen.getByRole("button", { name: "套用" }));
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls[1].searchParams.get("task_id")).toBeNull();
  expect(calls[1].searchParams.get("batch_id")).toBe("31");
  expect(calls[1].searchParams.get("from")).toBe("2026-11-01");
});

test("列捷徑只更新 draft；任務與專案導航由頁面處理", async () => {
  const user = userEvent.setup();
  const item = { ...historyFixtures.marked.items[0], batch_id: 31 };
  let calls = 0;
  server.use(http.get(`${API}/events`, () => { calls++; return HttpResponse.json({ items: [item], total: 1 }); }));
  open();
  await screen.findByRole("button", { name: "篩選批次 #31" });
  await user.click(screen.getByRole("button", { name: "篩選批次 #31" }));
  expect(screen.getByRole("spinbutton", { name: "批次編號" })).toHaveValue(31);
  expect(calls).toBe(1);
  await user.click(screen.getByRole("button", { name: "查看任務：舊任務名稱" }));
  expect(screen.getByText("任務詳情")).toBeInTheDocument();
});

test("分頁照伺服器順序與 total；成功空清單和 NOT_FOUND 分開", async () => {
  const user = userEvent.setup();
  const calls: URL[] = [];
  server.use(http.get(`${API}/events`, ({ request }) => { calls.push(new URL(request.url));
    return HttpResponse.json({ ...historyFixtures.marked, total: 101 }); }));
  open();
  await screen.findByText("舊任務名稱");
  expect(screen.getByText("符合 101 筆歷程")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "下一頁" }));
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls[1].searchParams.get("offset")).toBe("100");
  expect(within(screen.getByRole("list")).getAllByRole("listitem")).toHaveLength(1);
});

test("成功零筆顯示空態；404 顯示錯誤而不冒充零筆", async () => {
  server.use(http.get(`${API}/events`, () => HttpResponse.json(historyFixtures.empty)));
  const first = open();
  expect(await screen.findByText("沒有符合條件的歷程。") ).toBeInTheDocument();
  expect(screen.getByText("符合 0 筆歷程")).toBeInTheDocument();
  first.unmount();
  server.use(http.get(`${API}/events`, () => apiError(404, "NOT_FOUND")));
  open();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByText("沒有符合條件的歷程。")).not.toBeInTheDocument();
});

test("非任務事件顯示破折號；無專案事件標為單點任務", async () => {
  const item = { ...historyFixtures.marked.items[0], task_id: null, task_title: "", project_id: null, project_name: null };
  server.use(http.get(`${API}/events`, () => HttpResponse.json({ items: [item], total: 1 })));
  open();
  expect(await screen.findByRole("heading", { name: "—", level: 3 })).toBeInTheDocument();
  expect(screen.getByText("專案：單點任務")).toBeInTheDocument();
});

test("網址 offset 超過結果總數時回到最後有效頁，保留篩選", async () => {
  const calls: URL[] = [];
  server.use(http.get(`${API}/events`, ({ request }) => {
    const url = new URL(request.url);
    calls.push(url);
    return HttpResponse.json(url.searchParams.get("offset") === "200"
      ? { items: [], total: 101 } : { ...historyFixtures.marked, total: 101 });
  }));
  open("/history?kind=due&offset=200");
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls[1].searchParams.get("offset")).toBe("100");
  expect(calls[1].searchParams.get("kind")).toBe("due");
  expect(await screen.findByText("舊任務名稱")).toBeInTheDocument();
});

test.each([404, 401])("L1：真實 App 守門下 HistoryResults GET %s 不超過兩次", async status => {
  let calls = 0;
  localStorage.setItem("g4.token", "test-token");
  vi.stubGlobal("matchMedia", (media: string) => ({ matches: false, media,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  window.history.replaceState({}, "", "/history");
  server.use(http.get(`${API}/events`, () => { calls++; return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED"); }));
  try {
    render(<App />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await waitFor(() => expect(calls).toBeGreaterThan(0));
    expect(calls).toBeLessThanOrEqual(2);
  } finally {
    localStorage.removeItem("g4.token"); vi.unstubAllGlobals(); window.history.replaceState({}, "", "/");
  }
});
