import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";

import { App } from "../../App";
import { AppRoutes } from "../../app/AppRoutes";
import { goalFixtures } from "../../test/goalFixtures";
import { API, apiError, makeSettings, renderWithClient, server } from "../../test/server";

function open() {
  return renderWithClient(<MemoryRouter initialEntries={["/goals"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <AppRoutes />
  </MemoryRouter>);
}

beforeEach(() => server.use(
  http.get(`${API}/goals`, () => HttpResponse.json(goalFixtures.list)),
  http.get(`${API}/goals/1/stats`, () => HttpResponse.json(goalFixtures.insufficient)),
  http.get(`${API}/goals/2/stats`, () => HttpResponse.json(goalFixtures.timeStats)),
  http.get(`${API}/goals/3/stats`, () => HttpResponse.json(goalFixtures.expectationStats)),
  http.get(`${API}/goals/matrix`, () => HttpResponse.json(goalFixtures.matrix)),
  http.get(`${API}/goal-links/pending`, () => HttpResponse.json(goalFixtures.pending)),
  http.get(`${API}/projects`, () => HttpResponse.json(goalFixtures.projects)),
));

test("12.12 路由顯示目標管理、統計、矩陣與待關聯四區；不用預留頁", async () => {
  open();
  expect(await screen.findByRole("heading", { name: "目標與精力", level: 1 })).toBeInTheDocument();
  expect(await screen.findByRole("region", { name: "目標管理" })).toBeInTheDocument();
  expect(await screen.findByRole("region", { name: "目標統計" })).toBeInTheDocument();
  expect(await screen.findByRole("region", { name: "目標精力矩陣" })).toBeInTheDocument();
  expect(await screen.findByRole("region", { name: "待關聯任務" })).toBeInTheDocument();
  expect(screen.queryByText("此功能尚未開放。")).not.toBeInTheDocument();
});

test("FR-GOL-01／02：停用類型不能新增，既有目標仍可讀；類型與預期精力不預選", async () => {
  const user = userEvent.setup();
  server.use(http.get(`${API}/settings`, () => HttpResponse.json(makeSettings({ goal_types_enabled: ["growth"] }))));
  open();
  expect(await screen.findByText("安排確認時間")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "新增目標" }));
  const type = screen.getByLabelText("目標類型");
  expect(type).toHaveValue("");
  expect(within(type).queryByRole("option", { name: "時間配置" })).not.toBeInTheDocument();
  expect(screen.getByLabelText("預期精力")).toHaveValue("");
});

test("FR-GOL-01：建立 growth 僅送明選欄位，201 後重讀目標清單", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  let lists = 0;
  server.use(http.get(`${API}/goals`, () => { lists++; return HttpResponse.json(goalFixtures.list); }),
    http.post(`${API}/goals`, async ({ request }) => {
      bodies.push(await request.json()); return HttpResponse.json(goalFixtures.growth, { status: 201 });
    }));
  open();
  await user.click(await screen.findByRole("button", { name: "新增目標" }));
  await user.selectOptions(screen.getByLabelText("目標類型"), "growth");
  await user.type(screen.getByLabelText("名稱"), "練習規格分析");
  await user.type(screen.getByLabelText("期間"), "2026Q4");
  await user.selectOptions(screen.getByLabelText("預期精力"), "high");
  await user.type(screen.getByLabelText("衡量目標（件）"), "3");
  await user.click(screen.getByRole("button", { name: "儲存新目標" }));
  await waitFor(() => expect(bodies).toEqual([{ type: "growth", title: "練習規格分析", period: "2026Q4",
    energy_plan: "high", target: 3, project_id: null }]));
  await waitFor(() => expect(lists).toBeGreaterThanOrEqual(2));
});

test("B4：績效期待必選未封存專案，不送完成率目標值", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(http.post(`${API}/goals`, async ({ request }) => {
    bodies.push(await request.json()); return HttpResponse.json(goalFixtures.expectation, { status: 201 });
  }));
  open();
  await user.click(await screen.findByRole("button", { name: "新增目標" }));
  await user.selectOptions(screen.getByLabelText("目標類型"), "expectation");
  await user.type(screen.getByLabelText("名稱"), "完成專案");
  await user.type(screen.getByLabelText("期間"), "2026Q4");
  await user.selectOptions(screen.getByLabelText("預期精力"), "low");
  expect(screen.getByRole("button", { name: "儲存新目標" })).toBeDisabled();
  await user.selectOptions(screen.getByLabelText("指定專案"), "1");
  await user.click(screen.getByRole("button", { name: "儲存新目標" }));
  await waitFor(() => expect(bodies).toEqual([{ type: "expectation", title: "完成專案", period: "2026Q4",
    energy_plan: "low", project_id: 1 }]));
  expect(JSON.stringify(bodies)).not.toContain("pct");
});

test("A3：時間配置建立與編輯的衡量目標標明分鐘／週", async () => {
  const user = userEvent.setup();
  open();
  await user.click(await screen.findByRole("button", { name: "新增目標" }));
  await user.selectOptions(screen.getByLabelText("目標類型"), "time");
  expect(screen.getByLabelText("衡量目標（分鐘／週）")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "取消" }));
  await user.click(screen.getByRole("button", { name: "編輯安排確認時間" }));
  expect(screen.getByLabelText("編輯衡量目標（分鐘／週）")).toBeInTheDocument();
});

test("PATCH 只送更動欄位；封存目標仍可編輯", async () => {
  const user = userEvent.setup();
  const patches: unknown[] = [];
  server.use(http.patch(`${API}/goals/4`, async ({ request }) => {
    patches.push(await request.json()); return HttpResponse.json({ goal: { ...goalFixtures.archived, title: "封存後更名" }, changes: [] });
  }));
  open();
  await user.click(await screen.findByRole("button", { name: "編輯已封存練習" }));
  const title = screen.getByLabelText("編輯名稱");
  await user.clear(title);
  await user.type(title, "封存後更名");
  await user.click(screen.getByRole("button", { name: "儲存修改" }));
  await waitFor(() => expect(patches).toEqual([{ title: "封存後更名" }]));
});

test("封存先確認，取消不 POST；確認後失效清單", async () => {
  const user = userEvent.setup();
  let posts = 0;
  let lists = 0;
  server.use(http.post(`${API}/goals/1/archive`, () => { posts++; return HttpResponse.json(goalFixtures.archived); }),
    http.get(`${API}/goals`, () => { lists++; return HttpResponse.json(goalFixtures.list); }));
  open();
  await user.click(await screen.findByRole("button", { name: "封存練習規格分析" }));
  await user.click(screen.getByRole("button", { name: "取消" }));
  expect(posts).toBe(0);
  await user.click(screen.getByRole("button", { name: "封存練習規格分析" }));
  await user.click(screen.getByRole("button", { name: "確認" }));
  await waitFor(() => expect(posts).toBe(1));
  await waitFor(() => expect(lists).toBeGreaterThanOrEqual(2));
});

test("AC-46／G2：樣本不足只呈現伺服器 note；零樣本平均 null 不補零", async () => {
  server.use(http.get(`${API}/goals/1/stats`, () => HttpResponse.json(goalFixtures.zeroStats)));
  open();
  const stats = await screen.findByRole("region", { name: "目標統計" });
  expect(await within(stats).findByText(goalFixtures.zeroStats.judgement_note)).toBeInTheDocument();
  expect(within(stats).queryByText("一致")).not.toBeInTheDocument();
  expect(within(stats).getByText("平均實際星數").nextElementSibling).toHaveTextContent("—");
  expect(within(stats).getByText("平均預設星數").nextElementSibling).toHaveTextContent("—");
  expect(within(stats).getByText("進度比例").nextElementSibling).toHaveTextContent("—");
});

test("B3／B4／G2：time progress=null，expectation 百分比與並列判讀皆照伺服器值", async () => {
  const user = userEvent.setup();
  server.use(http.get(`${API}/goals/3/stats`, () => HttpResponse.json(goalFixtures.tiedStats)));
  open();
  await user.click(await screen.findByRole("button", { name: "查看安排確認時間統計" }));
  const stats = await screen.findByRole("region", { name: "目標統計" });
  expect(await within(stats).findByText("主要精力為中，與預期相同")).toBeInTheDocument();
  expect(within(stats).getByRole("heading", { name: "目標統計：安排確認時間" })).toBeInTheDocument();
  expect(within(stats).queryByText("進度")).not.toBeInTheDocument();
  expect(within(stats).queryByText("進度比例")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "查看完成專案統計" }));
  expect(await within(stats).findByText("主要精力並列：高、中")).toBeInTheDocument();
  expect(within(stats).getByRole("heading", { name: "目標統計：完成專案" })).toBeInTheDocument();
  expect(within(stats).getByText("建議檢視")).toBeInTheDocument();
});

test("B4：績效期待進度百分比只顯示伺服器回應", async () => {
  const user = userEvent.setup();
  open();
  await user.click(await screen.findByRole("button", { name: "查看完成專案統計" }));
  const stats = screen.getByRole("region", { name: "目標統計" });
  expect(await within(stats).findByText(goalFixtures.expectationStats.judgement_note)).toBeInTheDocument();
  expect(within(stats).getByText("進度比例").nextElementSibling).toHaveTextContent("50%");
});

test("矩陣只讀 items，不從任務自算分布", async () => {
  open();
  const matrix = await screen.findByRole("region", { name: "目標精力矩陣" });
  expect(await within(matrix).findByText("練習規格分析")).toBeInTheDocument();
  expect(within(matrix).getByText("2")).toBeInTheDocument();
});

test("G1：pending 不觸發 AI；人明選目標並送 expected_version，成功重讀相關區塊", async () => {
  const user = userEvent.setup();
  let pendingGets = 0; let posts = 0; let suggests = 0; let goalsGets = 0; let statsGets = 0; let matrixGets = 0;
  const bodies: unknown[] = [];
  server.use(http.get(`${API}/goals`, () => { goalsGets++; return HttpResponse.json(goalFixtures.list); }),
    http.get(`${API}/goals/1/stats`, () => { statsGets++; return HttpResponse.json(goalFixtures.insufficient); }),
    http.get(`${API}/goals/matrix`, () => { matrixGets++; return HttpResponse.json(goalFixtures.matrix); }),
    http.get(`${API}/goal-links/pending`, () => {
    pendingGets++; return HttpResponse.json(posts ? goalFixtures.emptyPending : goalFixtures.pending);
  }), http.post(`${API}/goal-links`, async ({ request }) => {
    posts++; bodies.push(await request.json()); return HttpResponse.json(goalFixtures.linkResult);
  }), http.post(`${API}/goal-links/suggest`, () => { suggests++; return HttpResponse.json({}); }));
  open();
  const pending = await screen.findByRole("region", { name: "待關聯任務" });
  const goalSelect = await within(pending).findByLabelText("範例已完成任務的關聯目標");
  await screen.findByText(goalFixtures.insufficient.judgement_note);
  await within(screen.getByRole("region", { name: "目標精力矩陣" })).findByText("練習規格分析");
  expect(goalSelect).toHaveValue("");
  expect(suggests).toBe(0);
  await user.selectOptions(goalSelect, "1");
  await user.click(within(pending).getByRole("button", { name: "確認範例已完成任務關聯" }));
  await waitFor(() => expect(bodies).toEqual([{ task_id: 101, goal_id: 1, expected_version: 4 }]));
  expect(await within(pending).findByText("沒有待關聯任務。")).toBeInTheDocument();
  expect(pendingGets).toBeGreaterThanOrEqual(2);
  await waitFor(() => expect([goalsGets, statsGets, matrixGets].every(count => count >= 2)).toBe(true));
  expect(suggests).toBe(0);
});

test("G1：明選不關聯才送 goal_id=null", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(http.post(`${API}/goal-links`, async ({ request }) => {
    bodies.push(await request.json()); return HttpResponse.json(goalFixtures.linkResult);
  }));
  open();
  await user.selectOptions(await screen.findByLabelText("範例已完成任務的關聯目標"), "none");
  await user.click(screen.getByRole("button", { name: "確認範例已完成任務關聯" }));
  await waitFor(() => expect(bodies).toEqual([{ task_id: 101, goal_id: null, expected_version: 4 }]));
});

test("STALE_VERSION 重讀 pending、清除選擇，不自動重送；NO_CHANGE 顯示已無變更", async () => {
  const user = userEvent.setup();
  let gets = 0; let posts = 0;
  server.use(http.get(`${API}/goal-links/pending`, () => {
    gets++; return HttpResponse.json(gets === 1 ? goalFixtures.pending
      : { ...goalFixtures.pending, items: [{ ...goalFixtures.pending.items[0], version: 5 }] });
  }), http.post(`${API}/goal-links`, () => {
    posts++; return apiError(posts === 1 ? 409 : 422, posts === 1 ? "STALE_VERSION" : "NO_CHANGE");
  }));
  open();
  await user.selectOptions(await screen.findByLabelText("範例已完成任務的關聯目標"), "1");
  await user.click(screen.getByRole("button", { name: "確認範例已完成任務關聯" }));
  await waitFor(() => expect(gets).toBeGreaterThanOrEqual(2));
  expect(posts).toBe(1);
  expect(screen.getByLabelText("範例已完成任務的關聯目標")).toHaveValue("");
  expect(screen.getByText("資料已被其他操作更新，已重新載入，請確認後再操作一次。")).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("範例已完成任務的關聯目標"), "1");
  await user.click(screen.getByRole("button", { name: "確認範例已完成任務關聯" }));
  expect(await screen.findByText("目前關聯未變更。")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(posts).toBe(2);
});

test("A1：STALE_VERSION 後列從 pending 消失時，區塊保留處理提示", async () => {
  const user = userEvent.setup();
  let gets = 0; let posts = 0;
  server.use(http.get(`${API}/goal-links/pending`, () => {
    gets++;
    return HttpResponse.json(gets === 1 ? goalFixtures.pending : goalFixtures.emptyPending);
  }), http.post(`${API}/goal-links`, () => { posts++; return apiError(409, "STALE_VERSION"); }));
  open();
  await user.selectOptions(await screen.findByLabelText("範例已完成任務的關聯目標"), "1");
  await user.click(screen.getByRole("button", { name: "確認範例已完成任務關聯" }));
  const pending = screen.getByRole("region", { name: "待關聯任務" });
  expect(await within(pending).findByText("待關聯任務已在其他地方處理，清單已更新。")).toBeInTheDocument();
  expect(within(pending).getByText("沒有待關聯任務。")).toBeInTheDocument();
  expect(within(pending).queryByLabelText("範例已完成任務的關聯目標")).not.toBeInTheDocument();
  expect(posts).toBe(1);
});

test("#89 fast-follow：STALE_VERSION 使矩陣與各目標統計重讀", async () => {
  const user = userEvent.setup();
  let matrix = 0; let stats = 0;
  server.use(http.get(`${API}/goals/matrix`, () => { matrix++; return HttpResponse.json(goalFixtures.matrix); }),
    http.get(`${API}/goals/1/stats`, () => { stats++; return HttpResponse.json(goalFixtures.insufficient); }),
    http.post(`${API}/goal-links`, () => apiError(409, "STALE_VERSION")));
  open();
  await user.selectOptions(await screen.findByLabelText("範例已完成任務的關聯目標"), "1");
  await waitFor(() => expect(matrix).toBe(1));
  await waitFor(() => expect(stats).toBe(1));
  await user.click(screen.getByRole("button", { name: "確認範例已完成任務關聯" }));
  await waitFor(() => expect(matrix).toBeGreaterThanOrEqual(2));
  await waitFor(() => expect(stats).toBeGreaterThanOrEqual(2));
});

test("#89 fast-follow：新一次確認時清掉上次列消失的提示", async () => {
  const user = userEvent.setup();
  let posts = 0;
  server.use(http.get(`${API}/goal-links/pending`, () => HttpResponse.json({ ...goalFixtures.pending,
    items: posts === 0 ? goalFixtures.pending.items : [{ ...goalFixtures.pending.items[0], task_id: 102, title: "第二項範例任務" }],
  })), http.post(`${API}/goal-links`, () => {
    posts++;
    return apiError(posts === 1 ? 409 : 422, posts === 1 ? "STALE_VERSION" : "NO_CHANGE");
  }));
  open();
  await user.selectOptions(await screen.findByLabelText("範例已完成任務的關聯目標"), "1");
  await user.click(screen.getByRole("button", { name: "確認範例已完成任務關聯" }));
  expect(await screen.findByText("待關聯任務已在其他地方處理，清單已更新。")).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("第二項範例任務的關聯目標"), "1");
  await user.click(screen.getByRole("button", { name: "確認第二項範例任務關聯" }));
  expect(screen.queryByText("待關聯任務已在其他地方處理，清單已更新。")).not.toBeInTheDocument();
  expect(await screen.findByText("目前關聯未變更。")).toBeInTheDocument();
});

test("四區載入狀態分離，清單尚未回來時統計不虛構零值", async () => {
  let releaseGoals!: () => void; let releaseMatrix!: () => void; let releasePending!: () => void;
  const goalsHold = new Promise<void>(resolve => { releaseGoals = resolve; });
  const matrixHold = new Promise<void>(resolve => { releaseMatrix = resolve; });
  const pendingHold = new Promise<void>(resolve => { releasePending = resolve; });
  server.use(http.get(`${API}/goals`, async () => { await goalsHold; return HttpResponse.json(goalFixtures.list); }),
    http.get(`${API}/goals/matrix`, async () => { await matrixHold; return HttpResponse.json(goalFixtures.matrix); }),
    http.get(`${API}/goal-links/pending`, async () => { await pendingHold; return HttpResponse.json(goalFixtures.pending); }));
  open();
  expect(screen.getByText("載入目標清單中…")).toBeInTheDocument();
  expect(screen.getByText("選擇目標後查看統計。")).toBeInTheDocument();
  expect(screen.getByText("載入矩陣中…")).toBeInTheDocument();
  expect(screen.getByText("載入待關聯任務中…")).toBeInTheDocument();
  releaseGoals(); releaseMatrix(); releasePending();
  expect(await screen.findByText(goalFixtures.insufficient.judgement_note)).toBeInTheDocument();
});

test("各 GET 區塊的成功空狀態與錯誤狀態分開，不把失敗當零筆", async () => {
  server.use(http.get(`${API}/goals`, () => HttpResponse.json(goalFixtures.emptyList)),
    http.get(`${API}/goals/matrix`, () => HttpResponse.json(goalFixtures.emptyMatrix)),
    http.get(`${API}/goal-links/pending`, () => HttpResponse.json(goalFixtures.emptyPending)));
  const empty = open();
  expect(await screen.findByText("尚無目標。")).toBeInTheDocument();
  expect(screen.getByText("尚無矩陣資料。")).toBeInTheDocument();
  expect(screen.getByText("沒有待關聯任務。")).toBeInTheDocument();
  empty.unmount();
  server.use(http.get(`${API}/goals`, () => apiError(401, "UNAUTHORIZED")));
  open();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByText("尚無目標。")).not.toBeInTheDocument();
});

test.each([404, 401])("L1：真實守門下四種目標 GET 回 %s 時各請求數 ≤2", async status => {
  const counts = { goals: 0, stats: 0, matrix: 0, pending: 0 };
  localStorage.setItem("g4.token", "test-token");
  vi.stubGlobal("matchMedia", (media: string) => ({ matches: false, media,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  window.history.replaceState({}, "", "/goals");
  server.use(http.get(`${API}/goals`, () => { counts.goals++; return HttpResponse.json(goalFixtures.list); }),
    http.get(`${API}/goals/1/stats`, () => { counts.stats++; return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED"); }),
    http.get(`${API}/goals/matrix`, () => { counts.matrix++; return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED"); }),
    http.get(`${API}/goal-links/pending`, () => { counts.pending++; return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED"); }));
  try {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "目標與精力" })).toBeInTheDocument();
    await waitFor(() => expect(counts.stats && counts.matrix && counts.pending).toBeGreaterThan(0));
    expect(Object.values(counts).every(count => count <= 2)).toBe(true);
    expect((await screen.findAllByRole("alert")).length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByText("尚無矩陣資料。")).not.toBeInTheDocument();
    expect(screen.queryByText("沒有待關聯任務。")).not.toBeInTheDocument();
  } finally { localStorage.removeItem("g4.token"); vi.unstubAllGlobals(); window.history.replaceState({}, "", "/"); }
});

test.each([404, 401])("L1：真實守門下 goals GET 回 %s 不無限重送", async status => {
  let calls = 0;
  localStorage.setItem("g4.token", "test-token");
  vi.stubGlobal("matchMedia", (media: string) => ({ matches: false, media,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  window.history.replaceState({}, "", "/goals");
  server.use(http.get(`${API}/goals`, () => { calls++; return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED"); }));
  try {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "目標與精力" })).toBeInTheDocument();
    await waitFor(() => expect(calls).toBeGreaterThan(0));
    expect(calls).toBeLessThanOrEqual(2);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  } finally { localStorage.removeItem("g4.token"); vi.unstubAllGlobals(); window.history.replaceState({}, "", "/"); }
});
