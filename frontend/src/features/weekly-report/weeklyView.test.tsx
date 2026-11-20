import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ManualWeeklySection, WeekSelector, WeeklyAISection, WeeklyReportColumns } from "./weeklyView";
import { mondayOf, weeklyDisplay } from "./weeklyState";

describe("週報週次與展示閘門", () => {
  it.each([
    ["2026-11-15", "2026-11-09"], // 週日
    ["2026-12-01", "2026-11-30"], // 跨月
    ["2027-01-01", "2026-12-28"], // 跨年
  ])("選擇 %s 取得該週週一 %s", (selected, monday) => {
    expect(mondayOf(selected)).toBe(monday);
  });

  it("選日只通知新週次，不自行讀取或產稿", () => {
    const onSelectWeek = vi.fn();
    render(<WeekSelector weekStart="2026-11-09" onSelectWeek={onSelectWeek} />);
    fireEvent.change(screen.getByLabelText("選擇週次"), { target: { value: "2026-11-15" } });
    expect(onSelectWeek).toHaveBeenCalledExactlyOnceWith("2026-11-09");
  });

  it("validated=false 即使夾帶初稿，也不掛載初稿內容", () => {
    expect(weeklyDisplay(false, "ok", "不可洩露的 AI 初稿")).toBe("events");
    render(<WeeklyAISection validated={false} aiStatus="ok" draft="不可洩露的 AI 初稿" fallback={<p>範例事件</p>} />);
    expect(screen.queryByText("不可洩露的 AI 初稿")).not.toBeInTheDocument();
    expect(screen.getByText("範例事件")).toBeInTheDocument();
    expect(screen.getByText("初稿未通過歷程核對，以下為依目前歷程列出的事件清單")).toBeInTheDocument();
  });

  it("AI 降級仍顯示事件退路，不當成 HTTP 錯誤", () => {
    render(<WeeklyAISection validated={false} aiStatus="unavailable" draft={null} fallback={<p>範例事件</p>} />);
    expect(screen.getByText("範例事件")).toBeInTheDocument();
    expect(screen.getByText("AI 暫時無法使用，以下顯示可用內容。")).toBeInTheDocument();
  });

  it("只有 ok、通過核對且草稿有字才展示 AI 內容", () => {
    expect(weeklyDisplay(true, "ok", "初稿")).toBe("draft");
    expect(weeklyDisplay(true, "ok", null)).toBe("events");
    expect(weeklyDisplay(true, null, "初稿")).toBe("not-generated");
    render(<WeeklyAISection validated aiStatus="ok" draft="範例 AI 初稿" fallback={<p>範例事件</p>} />);
    expect(screen.getByText("範例 AI 初稿")).toBeInTheDocument();
  });
});

describe("週報人工版與版面骨架", () => {
  it("AI 與人工版分欄且語意順序固定", () => {
    const { container } = render(<WeeklyReportColumns ai={<p>AI 初稿</p>} manual={<p>人工版</p>} />);
    expect(container.textContent).toBe("AI 初稿人工版");
  });

  it("人工版只顯示受控草稿，儲存中暫停編輯並防連按", () => {
    const onChange = vi.fn();
    const onSave = vi.fn();
    const { rerender } = render(<ManualWeeklySection draft="我寫的內容" onChange={onChange} onSave={onSave} saving={false} />);
    expect(screen.getByLabelText("人工版")).toHaveValue("我寫的內容");
    fireEvent.change(screen.getByLabelText("人工版"), { target: { value: "新內容" } });
    expect(onChange).toHaveBeenCalledExactlyOnceWith("新內容");
    fireEvent.click(screen.getByRole("button", { name: "儲存人工版" }));
    expect(onSave).toHaveBeenCalledOnce();
    rerender(<ManualWeeklySection draft="我寫的內容" onChange={onChange} onSave={onSave} saving />);
    expect(screen.getByLabelText("人工版")).toBeDisabled();
    expect(screen.getByRole("button", { name: "儲存中…" })).toBeDisabled();
  });

  it("複製目前人工版文字並顯示成功提示，不取 AI 初稿", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const previous = Object.getOwnPropertyDescriptor(navigator, "clipboard");
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    try {
      const { rerender } = render(<WeeklyReportColumns ai={<p>AI 產生的文字</p>}
        manual={<><h2>人工版</h2><ManualWeeklySection draft="原人工版" onChange={vi.fn()} onSave={vi.fn()} saving={false} /></>} />);
      rerender(<WeeklyReportColumns ai={<p>AI 產生的文字</p>}
        manual={<><h2>人工版</h2><ManualWeeklySection draft="修改後的人工版" onChange={vi.fn()} onSave={vi.fn()} saving={false} /></>} />);
      fireEvent.click(screen.getByRole("button", { name: "複製" }));
      expect(writeText).toHaveBeenCalledExactlyOnceWith("修改後的人工版");
      expect(await screen.findByText("已複製")).toBeInTheDocument();
      expect(screen.getByRole("region", { name: "AI 初稿區" })).not.toHaveTextContent("已複製");
    } finally {
      if (previous) Object.defineProperty(navigator, "clipboard", previous);
      else Reflect.deleteProperty(navigator, "clipboard");
    }
  });

  it("人工版空白時不可複製", () => {
    render(<ManualWeeklySection draft="" onChange={vi.fn()} onSave={vi.fn()} saving={false} />);
    expect(screen.getByRole("button", { name: "複製" })).toBeDisabled();
  });
});
