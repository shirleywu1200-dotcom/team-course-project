import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { DatePicker } from "./DatePicker";
import { ConfirmationPanel } from "./ConfirmationPanel";
import { MarkChoice, markPayload, type MarkValue } from "./MarkChoice";
import { ReasonSelect } from "./ReasonSelect";
import { ErrorBanner } from "./ErrorBanner";
import { ReasonSelect as LegacyReasonSelect } from "./standin/ReasonSelect";
import { reasons } from "../test/reasons";
import { ApiError } from "../api/client";

test("日期選擇不預填，送出 YYYY-MM-DD 原字串，不轉時區", () => {
  const change = vi.fn();
  const view = render(<DatePicker id="due" label="最新預計" value="" onChange={change} />);
  expect(screen.getByLabelText("最新預計")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("最新預計"), { target: { value: "2026-11-18" } });
  expect(change).toHaveBeenCalledWith("2026-11-18");
  view.rerender(<DatePicker id="due" label="最新預計" value="2026-11-18" onChange={change} />);
  expect(screen.getByText("2026-11-18")).toBeVisible();
});

test("確認面板由呼叫者明確允許才可確認，取消不觸發確認", () => {
  const confirm = vi.fn(), cancel = vi.fn();
  const props = { title: "確認調整", onConfirm: confirm, onCancel: cancel };
  const view = render(<ConfirmationPanel {...props}><p>確認前不寫入</p></ConfirmationPanel>);
  expect(screen.getByRole("button", { name: "確認" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "取消" }));
  expect(cancel).toHaveBeenCalledTimes(1); expect(confirm).not.toHaveBeenCalled();
  view.rerender(<ConfirmationPanel {...props} canConfirm><p>確認前不寫入</p></ConfirmationPanel>);
  fireEvent.click(screen.getByRole("button", { name: "確認" }));
  expect(confirm).toHaveBeenCalledTimes(1);
});

function MarkForm({ external = false }: { external?: boolean }) {
  const [mark, setMark] = useState<MarkValue>(null);
  return <MarkChoice name="mark" value={mark} onChange={setMark} externalHint={external} />;
}

test("FR-MRK-01 三選一與稍後註記按既有順序，預設均不選", () => {
  render(<MarkForm />);
  expect(screen.getAllByRole("radio").map(input => (input as HTMLInputElement).value)).toEqual(["better", "worse", "none", "defer"]);
  for (const radio of screen.getAllByRole("radio")) expect(radio).not.toBeChecked();
  fireEvent.click(screen.getByRole("radio", { name: "稍後註記" }));
  expect(screen.getByRole("radio", { name: "稍後註記" })).toBeChecked();
  expect(markPayload("defer")).toEqual({ mark: null, defer_mark: true });
  expect(markPayload(null)).toEqual({ mark: null, defer_mark: false });
});

test.each(["變好", "變差", "不計入"])("註記 %s 只能由使用者選擇", label => {
  render(<MarkForm external />);
  for (const radio of screen.getAllByRole("radio")) expect(radio).not.toBeChecked();
  expect(screen.getByRole("note")).toHaveTextContent("建議選「不計入」");
  fireEvent.click(screen.getByRole("radio", { name: label }));
  expect(screen.getByRole("radio", { name: label })).toBeChecked();
});

test("原因不預選，依方向篩選；外部原因只提示，不代選註記", () => {
  function Form() {
    const [reason, setReason] = useState("");
    return <><ReasonSelect id="reason" reasons={reasons.due} direction="later" value={reason} onChange={setReason} /><MarkForm /></>;
  }
  render(<Form />);
  expect(screen.getByLabelText("原因")).toHaveValue("");
  expect(screen.queryByRole("option", { name: "提早完成條件達成" })).not.toBeInTheDocument();
  expect(screen.queryByRole("note")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("原因"), { target: { value: "wait_external" } });
  expect(screen.getByRole("note")).toHaveTextContent("這只是提示");
  for (const radio of screen.getAllByRole("radio")) expect(radio).not.toBeChecked();
});

test("未定方向停用原因；舊路徑把外部提示留給既有 MarkChoice，不重複顯示", () => {
  const props = { id: "reason", reasons: reasons.due, value: "", onChange: vi.fn() };
  const view = render(<ReasonSelect {...props} direction={null} />);
  expect(screen.getByLabelText("原因")).toBeDisabled();
  view.rerender(<><LegacyReasonSelect {...props} direction="later" value="wait_external" /><MarkForm external /></>);
  expect(screen.getAllByRole("note")).toHaveLength(1);
});

test("錯誤橫幅沿用既有訊息與未知錯誤退路，不顯示空橫幅", () => {
  const view = render(<ErrorBanner error={null} />);
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  view.rerender(<ErrorBanner error={new ApiError(409, "STALE_VERSION", "example")} />);
  expect(screen.getByRole("alert")).toHaveTextContent("已重新載入");
  view.rerender(<ErrorBanner error={new Error("private-example")} />);
  expect(screen.getByRole("alert")).toHaveTextContent("發生未預期的錯誤");
  expect(screen.getByRole("alert")).not.toHaveTextContent("private-example");
});
