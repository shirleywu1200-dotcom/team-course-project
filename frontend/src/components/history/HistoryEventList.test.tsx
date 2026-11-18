import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { historyFixtures } from "../../test/fixtures";
import { HistoryEventList } from "./HistoryEventList";

test("AC-29：歷程列顯示事件當時的任務名稱與 mine，不以現任務覆蓋", () => {
  render(<HistoryEventList items={historyFixtures.marked.items} />);
  const item = screen.getByRole("listitem");
  expect(within(item).getByText("舊任務名稱")).toBeInTheDocument();
  expect(item).toHaveTextContent("我的任務");
  expect(item).toHaveTextContent("2026-11-18");
  expect(item).toHaveTextContent("2026-11-20");
  expect(item).toHaveTextContent("原註記：變差");
  expect(item).toHaveTextContent("有效註記：不計入");
  expect(screen.queryByRole("button", { name: /編輯事件|刪除事件/ })).not.toBeInTheDocument();
});

test("AC-28：原文清除仍保留歷程與來源標籤；沒有原文但未清除時不誤稱已刪除", () => {
  const { rerender } = render(<HistoryEventList items={historyFixtures.purged.items} />);
  expect(screen.getByText("（原文已依設定刪除）")).toBeInTheDocument();
  expect(screen.getByText("收件來源")).toBeInTheDocument();
  rerender(<HistoryEventList items={historyFixtures.marked.items} />);
  expect(screen.queryByText("（原文已依設定刪除）")).not.toBeInTheDocument();
});

test("AC-08／10：只有我的非零 due 事件提供補或改註記入口", async () => {
  const user = userEvent.setup();
  const onAnnotate = vi.fn();
  const { rerender } = render(<HistoryEventList items={historyFixtures.unmarked.items} onAnnotate={onAnnotate} />);
  await user.click(screen.getByRole("button", { name: "補註記" }));
  expect(onAnnotate).toHaveBeenCalledWith(historyFixtures.unmarked.items[0]);
  rerender(<HistoryEventList items={historyFixtures.marked.items} onAnnotate={onAnnotate} />);
  expect(screen.getByRole("button", { name: "改註記" })).toBeInTheDocument();
  rerender(<HistoryEventList items={historyFixtures.otherOwner.items} onAnnotate={onAnnotate} />);
  expect(screen.queryByRole("button", { name: /註記/ })).not.toBeInTheDocument();
});
