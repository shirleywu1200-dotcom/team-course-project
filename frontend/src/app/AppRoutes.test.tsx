import { act, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, useLocation } from "react-router-dom";
import { vi } from "vitest";

import { API, makeTask, renderWithClient, server } from "../test/server";
import { AppRoutes } from "./AppRoutes";
import { timeManagementFixtures } from "../test/fixtures";

function LocationProbe() {
  const location = useLocation();
  return <output aria-label="目前網址">{location.pathname + location.search + location.hash}</output>;
}

function open(path: string) {
  return renderWithClient(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppRoutes />
      <LocationProbe />
    </MemoryRouter>,
  );
}

function viewport(compact: boolean) {
  const listeners = new Set<() => void>();
  const media = {
    matches: compact,
    media: "(max-width: 767px)",
    addEventListener: (_: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_: string, listener: () => void) => listeners.delete(listener),
  };
  vi.stubGlobal("matchMedia", () => media);
  return (value: boolean) => act(() => {
    media.matches = value;
    listeners.forEach((listener) => listener());
  });
}

beforeEach(() => {
  viewport(false);
  server.use(http.get(`${API}/reports/weekly`, () => HttpResponse.json({ error: { code: "NOT_FOUND", message: "未產生", details: {} } }, { status: 404 })));
});
afterEach(() => vi.unstubAllGlobals());

test.each([
  ["/projects", "專案現況"],
  ["/projects/1", "範例專案"],
  ["/tasks", "任務"],
  ["/tasks/new", "新增任務"],
  ["/history", "歷程"],
  ["/projects/1/history", "範例專案歷程"],
  ["/import", "匯入專案"],
  ["/inbox", "收件匣"],
  ["/today", "今日"],
  ["/tasks/4/feedback", "完成回報"],
  ["/time-management", "時間管理統計"],
  ["/setup", "開始設定"],
  ["/settings", "設定"],
  ["/goals", "目標與精力"],
  ["/reports", "週報"],
  ["/data-control", "資料控制"],
])("路由 %s 可直接開啟；已實作頁讀取資料，其餘仍預留", async (path, title) => {
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  try {
    open(path);
    expect(await screen.findByRole("heading", { name: title, level: 1 })).toBeInTheDocument();
    if (path === "/time-management") {
      expect(await screen.findByText(timeManagementFixtures.insufficient.judgement_note)).toBeInTheDocument();
      expect(screen.queryByText("此功能尚未開放。")).not.toBeInTheDocument();
      expect(fetchSpy).toHaveBeenCalled();
    } else if (["/import", "/inbox", "/setup", "/settings", "/reports", "/data-control", "/projects/1", "/history", "/projects/1/history"].includes(path)) {
      expect(screen.queryByText("此功能尚未開放。")).not.toBeInTheDocument();
      expect(fetchSpy).toHaveBeenCalled();
    } else {
      expect(screen.getByText("此功能尚未開放。")).toBeInTheDocument();
      expect(fetchSpy).not.toHaveBeenCalled();
    }
  } finally {
    fetchSpy.mockRestore();
  }
});

test("M1：每日確認連結留在收件匣；移除的 /confirmations 不再是預留頁", () => {
  const view = open("/");
  expect(screen.getByRole("link", { name: "每日確認" })).toHaveAttribute("href", "/inbox");
  view.unmount();
  open("/confirmations");
  expect(screen.getByRole("heading", { name: "找不到頁面" })).toBeInTheDocument();
});

test("首頁可透過導覽開啟頁面並標示目前位置", async () => {
  const user = userEvent.setup();
  open("/");
  expect(screen.getByRole("heading", { name: "工作總覽" })).toBeInTheDocument();
  const nav = screen.getByRole("navigation", { name: "主要導覽" });
  await user.click(within(nav).getByRole("link", { name: "歷程" }));
  expect(screen.getByRole("heading", { name: "歷程" })).toBeInTheDocument();
  expect(within(nav).getByRole("link", { name: "歷程" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByLabelText("目前網址")).toHaveTextContent("/history");
});

test("切換手機與網站版面保留同一個任務元件、網址與未送出輸入", async () => {
  const resize = viewport(false);
  server.use(http.get(`${API}/tasks/4`, () => HttpResponse.json({ task: makeTask() })));
  open("/tasks/4?from=history#adjust");
  await screen.findByRole("heading", { name: "確認驗收條件" });
  const input = screen.getByLabelText("新的預計完成日");
  fireEvent.change(input, { target: { value: "2026-11-20" } });
  const content = screen.getByRole("region", { name: "頁面內容" });
  expect(screen.getByTestId("app-shell")).toHaveAttribute("data-layout", "wide");
  resize(true);
  expect(screen.getByTestId("app-shell")).toHaveAttribute("data-layout", "compact");
  expect(screen.getByRole("region", { name: "頁面內容" })).toBe(content);
  expect(screen.getByLabelText("新的預計完成日")).toBe(input);
  expect(input).toHaveValue("2026-11-20");
  expect(screen.getByLabelText("目前網址")).toHaveTextContent("/tasks/4?from=history#adjust");
  resize(false);
  expect(screen.getByTestId("app-shell")).toHaveAttribute("data-layout", "wide");
  expect(screen.getByLabelText("新的預計完成日")).toBe(input);
  expect(input).toHaveValue("2026-11-20");
});

test("既有整批順延路由仍載入 Dev-A 頁面", async () => {
  server.use(http.get(`${API}/tasks`, () => HttpResponse.json({ items: [makeTask()], total: 1 })));
  open("/projects/1/bulk-shift");
  expect(await screen.findByRole("heading", { name: /整批順延/ })).toBeInTheDocument();
  expect(await screen.findByLabelText("選擇 確認驗收條件")).toBeInTheDocument();
});

test("手機底部導覽只顯示指定五個入口與順序", () => {
  viewport(true);
  open("/inbox");
  const nav = screen.getByRole("navigation", { name: "主要導覽" });
  expect(screen.getByTestId("app-shell")).toHaveAttribute("data-layout", "compact");
  expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual(["收件匣", "今日", "任務", "目標", "設定"]);
  expect(within(nav).getByRole("link", { name: "目標" })).toHaveAttribute("href", "/goals");
});

test("手機首頁保留其餘入口，仍可開啟未列於底部導覽的頁面", async () => {
  viewport(true);
  const user = userEvent.setup();
  open("/");
  const home = screen.getByRole("main");
  for (const label of ["專案現況", "歷程", "匯入專案", "時間管理統計", "週報", "資料控制"]) {
    expect(within(home).getByRole("link", { name: label })).toBeInTheDocument();
    expect(within(screen.getByRole("navigation", { name: "主要導覽" })).queryByRole("link", { name: label })).not.toBeInTheDocument();
  }
  await user.click(within(home).getByRole("link", { name: "週報" }));
  expect(screen.getByRole("heading", { name: "週報" })).toBeInTheDocument();
});

test("網站導覽維持完整，切換手機後再切回仍恢復全部入口", () => {
  const resize = viewport(false);
  open("/today");
  const labels = () => within(screen.getByRole("navigation", { name: "主要導覽" })).getAllByRole("link").map((link) => link.textContent);
  const desktop = ["專案現況", "任務", "歷程", "匯入專案", "收件匣", "今日", "時間管理統計", "設定", "目標與精力", "週報", "資料控制"];
  expect(labels()).toEqual(desktop);
  resize(true);
  expect(labels()).toEqual(["收件匣", "今日", "任務", "目標", "設定"]);
  resize(false);
  expect(labels()).toEqual(desktop);
});

test("未知路由顯示找不到頁面並可返回首頁", async () => {
  const user = userEvent.setup();
  open("/missing-page");
  expect(screen.getByRole("heading", { name: "找不到頁面" })).toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "回到工作總覽" }));
  expect(screen.getByRole("heading", { name: "工作總覽" })).toBeInTheDocument();
});
