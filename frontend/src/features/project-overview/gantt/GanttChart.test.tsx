import { fireEvent, render, screen, within } from "@testing-library/react";
import { GanttChart } from "./GanttChart";
import type { components } from "../../../api/types.generated";

type GanttOut = components["schemas"]["GanttOut"];

// 12.1 定稿中的 ganttFixture／emptyGanttFixture，固定範例、不接 API 或 MSW。
const ganttFixture: GanttOut = {
  range: { from: "2026-11-09", to: "2026-11-22" },
  today: "2026-11-16",
  summary: { done: 1, total: 3, delayed: 1, open_candidates: 2 },
  rows: [
    { task_id: 101, title: "範例任務甲", owner: "我", status: "doing",
      start: "2026-11-09", orig_due: "2026-11-18", latest_due: "2026-11-20",
      delta_days: 2, done_date: null, blocked: true, version: 4 },
    { task_id: 102, title: "範例任務乙", owner: "範例協作者", status: "todo",
      start: "2026-11-10", orig_due: "2026-11-22", latest_due: "2026-11-17",
      delta_days: -5, done_date: null, blocked: false, version: 2 },
    { task_id: 103, title: "範例任務丙", owner: "我", status: "done",
      start: "2026-11-11", orig_due: "2026-11-14", latest_due: "2026-11-14",
      delta_days: 0, done_date: "2026-11-13", blocked: false, version: 3 },
  ],
};
const emptyGanttFixture: GanttOut = {
  range: null, today: "2026-11-16",
  summary: { done: 0, total: 0, delayed: 0, open_candidates: 0 }, rows: [],
};
const appearance = { width: 484, leftLabelWidth: 200, rowHeight: 64 };
const row = (title: string) => screen.getByRole("group", { name: new RegExp(title) });
const marker = (title: string, name: string) => within(row(title)).getByLabelText(name);

test("FR-PRJ-05 進行條依 start→latest_due 映射到 range", () => {
  render(<GanttChart gantt={ganttFixture} {...appearance} />);
  const bar = marker("範例任務甲", "進行區間 2026-11-09 至 2026-11-20");
  expect(bar).toHaveAttribute("x", "200");
  expect(bar).toHaveAttribute("width", "220");
});

test("FR-PRJ-05 原訂基準框保留開始至原訂輪廓與獨立刻線，繪於延後段上方", () => {
  render(<GanttChart gantt={ganttFixture} {...appearance} />);
  const frame = marker("範例任務甲", "原訂基準框 2026-11-09 至 2026-11-18");
  const due = marker("範例任務甲", "原訂日 2026-11-18");
  const delay = marker("範例任務甲", "延後區間 2026-11-18 至 2026-11-20，延後 2 天");
  expect(frame).toHaveAttribute("x", "200");
  expect(frame).toHaveAttribute("width", "180");
  expect(frame).toHaveAttribute("fill", "none");
  expect(due).toHaveAttribute("x1", "380");
  expect(delay.compareDocumentPosition(frame) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(delay.compareDocumentPosition(due) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(marker("範例任務乙", "原訂日 2026-11-22")).toBeInTheDocument();
});

test("FR-PRJ-05 只有 latest_due 晚於 orig_due 才畫延後段", () => {
  render(<GanttChart gantt={ganttFixture} {...appearance} />);
  const delay = marker("範例任務甲", "延後區間 2026-11-18 至 2026-11-20，延後 2 天");
  expect(delay).toHaveAttribute("x", "380");
  expect(delay).toHaveAttribute("width", "40");
  expect(within(row("範例任務乙")).queryByLabelText(/^延後區間/)).not.toBeInTheDocument();
  expect(within(row("範例任務丙")).queryByLabelText(/^延後區間/)).not.toBeInTheDocument();
});

test("FR-PRJ-05 done 的進行條以 done_date 收尾且保留原訂框", () => {
  render(<GanttChart gantt={ganttFixture} {...appearance} />);
  expect(marker("範例任務丙", "進行區間 2026-11-11 至 2026-11-13")).toHaveAttribute("width", "40");
  expect(marker("範例任務丙", "完成日 2026-11-13")).toHaveAttribute("cx", "280");
  expect(marker("範例任務丙", "原訂日 2026-11-14")).toHaveAttribute("x1", "300");
});

test("done_date=null 不捏造完成點，未完成列也不畫完成點", () => {
  const fixture = structuredClone(ganttFixture);
  fixture.rows[2].done_date = null;
  fixture.rows[0].done_date = "2026-11-13";
  render(<GanttChart gantt={fixture} {...appearance} />);
  expect(row("範例任務丙")).toBeInTheDocument();
  expect(screen.queryByLabelText(/^完成日 /)).not.toBeInTheDocument();
});

test("FR-PRJ-05 已完成且逾期：進行條止於完成日、延後段保留至最新預計、完成點不被遮住", () => {
  const fixture: GanttOut = {
    ...ganttFixture,
    summary: { done: 1, total: 1, delayed: 1, open_candidates: 0 },
    rows: [{ ...ganttFixture.rows[2], start: "2026-11-11",
      orig_due: "2026-11-13", latest_due: "2026-11-16",
      done_date: "2026-11-15", status: "done", delta_days: 3 }],
  };
  render(<GanttChart gantt={fixture} {...appearance} />);
  const bar = marker("範例任務丙", "進行區間 2026-11-11 至 2026-11-15");
  const delay = marker("範例任務丙", "延後區間 2026-11-13 至 2026-11-16，延後 3 天");
  const done = marker("範例任務丙", "完成日 2026-11-15");

  // range 每天 20px：start=240、orig_due=280、done_date=320、latest_due=340。
  expect(bar).toHaveAttribute("x", "240");
  expect(bar).toHaveAttribute("width", "80");
  expect(delay).toHaveAttribute("x", "280");
  expect(delay).toHaveAttribute("width", "60");
  expect(done).toHaveAttribute("cx", "320");
  expect(Number(bar.getAttribute("x")) + Number(bar.getAttribute("width")))
    .toBe(Number(done.getAttribute("cx")));
  expect(Number(delay.getAttribute("x")) + Number(delay.getAttribute("width"))).toBe(340);

  // 同列保留三個獨立圖形；完成點最後繪製並突出條帶，不被延後段蓋掉。
  expect(bar.tagName.toLowerCase()).toBe("rect");
  expect(delay.tagName.toLowerCase()).toBe("rect");
  expect(done.tagName.toLowerCase()).toBe("circle");
  expect(bar.compareDocumentPosition(delay) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(delay.compareDocumentPosition(done) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(Number(done.getAttribute("cy")))
    .toBe(Number(bar.getAttribute("y")) + Number(bar.getAttribute("height")) / 2);
  expect(Number(done.getAttribute("r"))).toBeGreaterThan(Number(delay.getAttribute("height")) / 2);
});

test("今天線只取 props.today，系統時鐘改變也不影響；新 props 會移動線", () => {
  vi.useFakeTimers();
  try {
    vi.setSystemTime(new Date("2040-01-01T00:00:00Z"));
    const view = render(<GanttChart gantt={ganttFixture} {...appearance} />);
    expect(screen.getByLabelText("今天 2026-11-16")).toHaveAttribute("x1", "340");
    view.rerender(<GanttChart gantt={{ ...ganttFixture, today: "2026-11-17" }} {...appearance} />);
    expect(screen.getByLabelText("今天 2026-11-17")).toHaveAttribute("x1", "360");
  } finally {
    vi.useRealTimers();
  }
});

test("提前文字使用傳入 delta_days，即使與日期差不一致也不重算", () => {
  const fixture = structuredClone(ganttFixture);
  fixture.rows[1].delta_days = -9;
  render(<GanttChart gantt={fixture} {...appearance} />);
  expect(within(row("範例任務乙")).getByText(/提前 9 天/, { selector: "text" })).toBeInTheDocument();
  expect(screen.queryByText(/提前 5 天/)).not.toBeInTheDocument();
});

test("延後天數文字也取 props，不由座標反算", () => {
  const fixture = structuredClone(ganttFixture);
  fixture.rows[0].delta_days = 7;
  render(<GanttChart gantt={fixture} {...appearance} />);
  expect(marker("範例任務甲", "延後區間 2026-11-18 至 2026-11-20，延後 7 天")).toHaveAttribute("width", "40");
});

test.each([
  ["無範圍且無列", emptyGanttFixture],
  ["無範圍但有列", { ...ganttFixture, range: null }],
  ["有範圍但無列", { ...ganttFixture, rows: [] }],
])("%s 顯示空狀態，不虛構軸線、不丟錯", (_name, fixture) => {
  const { container } = render(<GanttChart gantt={fixture} />);
  expect(screen.getByText("此專案尚無可繪製的時間資料")).toBeInTheDocument();
  expect(container.querySelectorAll("line, rect, circle")).toHaveLength(0);
});

test("每列文字與 aria 可辨識任務、狀態、天數與阻塞，非純色辨識", () => {
  render(<GanttChart gantt={ganttFixture} />);
  expect(screen.getByRole("img", { name: "專案甘特圖" })).toBeInTheDocument();
  expect(row("範例任務甲")).toHaveAccessibleName(/範例任務甲.*進行中.*延後 2 天.*阻塞/);
  expect(row("範例任務乙")).toHaveAccessibleName(/範例任務乙.*待辦.*提前 5 天/);
  expect(row("範例任務丙")).toHaveAccessibleName(/範例任務丙.*已完成/);
  expect(within(row("範例任務甲")).getByText(/阻塞/, { selector: "text" })).toBeInTheDocument();
  expect(within(row("範例任務乙")).queryByText(/阻塞/)).not.toBeInTheDocument();
});

test("外觀預設值、dayWidth 與單日範圍均可繪出有限座標", () => {
  const single: GanttOut = { ...ganttFixture,
    range: { from: "2026-11-09", to: "2026-11-09" },
    today: "2026-11-09", rows: [{ ...ganttFixture.rows[0],
      orig_due: "2026-11-09", latest_due: "2026-11-09", delta_days: 0 }],
  };
  const { container, rerender } = render(<GanttChart gantt={single} dayWidth={30} />);
  expect(container.innerHTML).not.toMatch(/NaN|Infinity/);
  expect(screen.getByLabelText("原訂日 2026-11-09")).toBeInTheDocument();
  rerender(<GanttChart gantt={ganttFixture} leftLabelWidth={200} dayWidth={20} />);
  expect(screen.getByRole("img", { name: "專案甘特圖" })).toHaveAttribute("viewBox", "0 0 484 264");
});

test("純展示：render、重繪與點擊／拖曳不 fetch、不寫日期、不改 props，也沒有控制項", () => {
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  const fixture = structuredClone(ganttFixture);
  const before = structuredClone(fixture);
  try {
    const view = render(<GanttChart gantt={fixture} />);
    const chart = screen.getByRole("img", { name: "專案甘特圖" });
    fireEvent.click(chart);
    fireEvent.dragStart(chart);
    fireEvent.drop(chart);
    view.rerender(<GanttChart gantt={fixture} width={700} />);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(fixture).toEqual(before);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(view.container.querySelector("input, select, [draggable='true']")).toBeNull();
  } finally {
    fetchSpy.mockRestore();
  }
});
