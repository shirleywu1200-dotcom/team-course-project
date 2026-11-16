import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";

import { App } from "../../App";
import { keys, queryRoots } from "../../api/queryKeys";
import { timeManagementFixtures as fixtures } from "../../test/fixtures";
import { API, apiError, renderWithClient, server } from "../../test/server";
import { TimeManagementPage } from "./TimeManagementPage";

function RouterProbe() {
  const location = useLocation();
  const navigate = useNavigate();
  return <><span aria-label="目前網址">{location.pathname + location.search}</span>
    <button onClick={() => navigate(-1)}>上一頁</button><button onClick={() => navigate(1)}>下一頁</button></>;
}

function open(path = "/time-management") {
  return renderWithClient(<MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <TimeManagementPage /><RouterProbe />
  </MemoryRouter>);
}

function capture(response: () => Response | Promise<Response> = () => HttpResponse.json(fixtures.insufficient)) {
  const calls: URL[] = [];
  server.use(http.get(`${API}/stats/time-management`, ({ request }) => {
    calls.push(new URL(request.url));
    return response();
  }));
  return calls;
}

const setDate = (label: "起日" | "迄日", value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const apply = () => fireEvent.click(screen.getByRole("button", { name: "套用" }));
const note = (text = fixtures.insufficient.judgement_note) => screen.findByText(text, { exact: true });

test.each(Object.entries(fixtures))("定稿 fixture %s：六計數、判讀與說明逐欄讀取伺服器值", async (_name, fixture) => {
  capture(() => HttpResponse.json(fixture));
  open();
  expect(await note(fixture.judgement_note)).toBeVisible();
  for (const [label, value] of [
    ["變好次數", `${fixture.better.count} 次`], ["提前總天數", `${fixture.better.days} 天`],
    ["變差次數", `${fixture.worse.count} 次`], ["延後總天數", `${fixture.worse.days} 天`],
    ["不計入次數", `${fixture.none} 次`], ["未註記次數", `${fixture.unmarked} 次`],
  ]) expect(screen.getByLabelText(label)).toHaveTextContent(value);
  if (fixture.judgement === null) {
    expect(screen.queryByRole("heading", { name: "判讀結論" })).not.toBeInTheDocument();
    expect(screen.queryByText("持平", { exact: true })).not.toBeInTheDocument();
  } else {
    expect(screen.getByText(fixture.judgement, { exact: true })).toBeVisible();
  }
  const distribution = screen.getByRole("region", { name: "被標變差的任務完成時的精力分布" });
  for (const [label, value] of [["高精力", fixture.worse_by_energy.high], ["中精力", fixture.worse_by_energy.mid],
    ["低精力", fixture.worse_by_energy.low], ["尚未完成", fixture.worse_by_energy.not_done]] as const) {
    expect(within(distribution).getByLabelText(label)).toHaveTextContent(`${value} 個任務`);
  }
});

test("判讀與 note 即使換成另一組字串、門檻與計數不一致也原文顯示，不重判", async () => {
  capture(() => HttpResponse.json({ ...fixtures.empty, min_sample: 99,
    judgement: "伺服器指定的測試判讀", judgement_note: "伺服器指定的完整說明；原樣呈現。" }));
  open();
  expect(await note("伺服器指定的完整說明；原樣呈現。")).toBeVisible();
  expect(screen.getByText("伺服器指定的測試判讀", { exact: true })).toBeVisible();
});

test("judgement=null 才隱藏結論，不因前端計數足夠而補判讀", async () => {
  capture(() => HttpResponse.json({ ...fixtures.better, judgement: null, judgement_note: "由伺服器決定暫不判讀" }));
  open();
  expect(await note("由伺服器決定暫不判讀")).toBeVisible();
  expect(screen.queryByRole("heading", { name: "判讀結論" })).not.toBeInTheDocument();
  expect(screen.getByLabelText("變好次數")).toHaveTextContent("4 次");
});

test("not_done 獨立框不放入高中低組，並呈現分類說明", async () => {
  capture(() => HttpResponse.json(fixtures.notDone));
  open();
  await note(fixtures.notDone.judgement_note);
  const levels = screen.getByRole("group", { name: "精力等級" });
  expect(within(levels).queryByLabelText("尚未完成")).not.toBeInTheDocument();
  expect(screen.getByRole("group", { name: "尚未完成分類" })).toContainElement(screen.getByLabelText("尚未完成"));
  expect(screen.getByText("依端點分類，沒有完成回報的任務歸入此格；此格不是精力等級")).toBeVisible();
});

test("初次 loading 不顯示零計數或樣本不足，成功後才出現結果", async () => {
  let finish!: () => void;
  const pending = new Promise<void>(resolve => { finish = resolve; });
  capture(async () => { await pending; return HttpResponse.json(fixtures.empty); });
  open();
  expect(screen.getByText("載入統計中")).toHaveAttribute("role", "status");
  expect(screen.queryByLabelText("變好次數")).not.toBeInTheDocument();
  expect(screen.queryByText(fixtures.empty.judgement_note)).not.toBeInTheDocument();
  await act(async () => { finish(); });
  expect(await note(fixtures.empty.judgement_note)).toBeVisible();
  expect(screen.getByText("目前範圍無統計資料")).toBeVisible();
});

test("HTTP error 不當成空資料；重試成功，日期不清除", async () => {
  let failed = true;
  const calls = capture(() => failed ? apiError(500, "INTERNAL_ERROR") : HttpResponse.json(fixtures.better));
  open("/time-management?from=2026-11-01");
  expect(await screen.findByRole("alert")).toBeVisible();
  expect(screen.queryByText("目前範圍無統計資料")).not.toBeInTheDocument();
  expect(screen.getByLabelText("起日")).toHaveValue("2026-11-01");
  failed = false;
  fireEvent.click(screen.getByRole("button", { name: "重試" }));
  await note(fixtures.better.judgement_note);
  expect(calls).toHaveLength(2);
  expect(calls[1].search).toBe("?from=2026-11-01");
});

test.each([404, 401])("L1：真實 App 守門下 stats GET %s 請求數不超過兩次", async status => {
  let requests = 0;
  localStorage.setItem("g4.token", "test-token");
  vi.stubGlobal("matchMedia", (media: string) => ({ matches: false, media,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  window.history.replaceState({}, "", "/time-management");
  server.use(http.get(`${API}/stats/time-management`, () => {
    requests++;
    return apiError(status, status === 404 ? "NOT_FOUND" : "UNAUTHORIZED");
  }));
  try {
    render(<App />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await waitFor(() => expect(requests).toBeGreaterThan(0));
    await delay(100);
    expect(requests).toBeLessThanOrEqual(2);
  } finally {
    localStorage.removeItem("g4.token");
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  }
});

test("必填 judgement_note 缺漏是契約異常，不補空白或自拼樣本句", async () => {
  const { judgement_note: _note, ...broken } = fixtures.insufficient;
  capture(() => HttpResponse.json(broken));
  open();
  expect(await screen.findByRole("alert")).toBeVisible();
  expect(screen.queryByLabelText("變好次數")).not.toBeInTheDocument();
  expect(screen.queryByText(fixtures.insufficient.judgement_note)).not.toBeInTheDocument();
});

test.each([
  ["", "", ""], ["2026-11-01", "", "?from=2026-11-01"],
  ["", "2026-11-16", "?to=2026-11-16"],
  ["2026-11-01", "2026-11-16", "?from=2026-11-01&to=2026-11-16"],
])("from/to 選填：%s 到 %s，按套用才查並寫 URL", async (from, to, search) => {
  const calls = capture();
  const storage = vi.spyOn(Storage.prototype, "setItem");
  try {
    open();
    await note();
    expect(screen.getByLabelText("起日")).toHaveValue("");
    expect(screen.getByLabelText("迄日")).toHaveValue("");
    expect(calls[0].search).toBe("");
    setDate("起日", from); setDate("迄日", to);
    expect(calls).toHaveLength(1);
    apply();
    await waitFor(() => expect(screen.getByLabelText("目前網址")).toHaveTextContent(`/time-management${search}`));
    if (search) await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls.at(-1)?.search).toBe(search);
    expect(storage).not.toHaveBeenCalled();
  } finally { storage.mockRestore(); }
});

test("網址空值省略、query key 空值正規化為同一份，日期不換算", async () => {
  expect(keys.timeManagement({ from: "", to: undefined })).toEqual(keys.timeManagement());
  const calls = capture();
  open("/time-management?from=&to=2026-11-16");
  await note();
  expect(calls[0].search).toBe("?to=2026-11-16");
  expect(screen.getByLabelText("迄日")).toHaveValue("2026-11-16");
});

test("URL 初次還原單雙日期，不預填今天；保留其餘 URL 參數", async () => {
  const calls = capture();
  open("/time-management?from=2026-11-01&to=2026-11-16&view=counts");
  await note();
  expect(screen.getByLabelText("起日")).toHaveValue("2026-11-01");
  expect(screen.getByLabelText("迄日")).toHaveValue("2026-11-16");
  setDate("迄日", "2026-11-17"); apply();
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(screen.getByLabelText("目前網址")).toHaveTextContent("view=counts");
});

test("清空已套用的兩日期再套用，回查全部並移除 URL 日期鍵", async () => {
  const calls = capture();
  open("/time-management?from=2026-11-01&to=2026-11-16");
  await note();
  setDate("起日", ""); setDate("迄日", ""); apply();
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls[1].search).toBe("");
  expect(screen.getByLabelText("目前網址").textContent).toBe("/time-management");
});

test("起日大於迄日阻擋；不查、不覆寫 URL、不偷換日期、不清掉既有結果", async () => {
  const calls = capture();
  open(); await note();
  setDate("起日", "2026-11-17"); setDate("迄日", "2026-11-01"); apply();
  expect(screen.getByRole("alert")).toHaveTextContent("起日不得晚於迄日");
  expect(calls).toHaveLength(1);
  expect(screen.getByLabelText("目前網址").textContent).toBe("/time-management");
  expect(screen.getByLabelText("起日")).toHaveValue("2026-11-17");
  expect(screen.getByText(fixtures.insufficient.judgement_note)).toBeVisible();
});

test("網址本身起日晚於迄日也阻擋，沒有送出無效請求", () => {
  const calls = capture();
  open("/time-management?from=2026-11-17&to=2026-11-01");
  expect(screen.getByRole("alert")).toHaveTextContent("起日不得晚於迄日");
  expect(calls).toHaveLength(0);
  expect(screen.queryByText("載入統計中")).not.toBeInTheDocument();
});

test("前後導覽依 URL 還原表單與查詢範圍，草稿不覆蓋已套用條件", async () => {
  const user = userEvent.setup();
  const calls = capture();
  open(); await note();
  setDate("起日", "2026-11-01"); apply();
  await waitFor(() => expect(calls).toHaveLength(2));
  setDate("起日", "2026-11-02");
  await user.click(screen.getByRole("button", { name: "上一頁" }));
  await waitFor(() => expect(screen.getByLabelText("起日")).toHaveValue(""));
  await user.click(screen.getByRole("button", { name: "下一頁" }));
  await waitFor(() => expect(screen.getByLabelText("起日")).toHaveValue("2026-11-01"));
  expect(calls.at(-1)?.search).toBe("?from=2026-11-01");
});

test("換範圍 loading 不把上次結果當成新條件；同範圍背景重讀明示更新中", async () => {
  let block = false;
  let finish!: () => void;
  const pending = new Promise<void>(resolve => { finish = resolve; });
  capture(async () => { if (block) await pending; return HttpResponse.json(fixtures.better); });
  const { client } = open(); await note(fixtures.better.judgement_note);
  block = true;
  await act(async () => { void client.invalidateQueries({ queryKey: queryRoots.timeManagement }); });
  await waitFor(() => expect(screen.getByText("更新統計中")).toHaveAttribute("role", "status"));
  expect(screen.getByLabelText("變好次數")).toHaveTextContent("4 次");
  setDate("起日", "2026-11-01"); apply();
  expect(screen.getByText("載入統計中")).toHaveAttribute("role", "status");
  expect(screen.queryByLabelText("變好次數")).not.toBeInTheDocument();
  await act(async () => { finish(); });
  await note(fixtures.better.judgement_note);
});

test("精力分布是任務數，與變差事件次數不同也照回應顯示，不產生百分比", async () => {
  capture(async () => { await delay(10); return HttpResponse.json({ ...fixtures.better,
    worse: { count: 9, days: 21 }, worse_by_energy: { high: 1, mid: 0, low: 0, not_done: 1 } }); });
  open(); await note(fixtures.better.judgement_note);
  expect(screen.getByLabelText("變差次數")).toHaveTextContent("9 次");
  expect(screen.getByLabelText("高精力")).toHaveTextContent("1 個任務");
  expect(screen.getByLabelText("尚未完成")).toHaveTextContent("1 個任務");
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});
