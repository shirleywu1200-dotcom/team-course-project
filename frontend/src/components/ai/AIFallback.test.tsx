import { fireEvent, render, screen } from "@testing-library/react";
import { ApiError } from "../../api/client";
import { AIFallback } from "./AIFallback";
import { RubricInterviewFallback } from "./RubricInterviewFallback";

test("spec 5.3 ok 顯示既有內容，不顯示降級提示與退路", () => {
  render(<AIFallback aiStatus="ok" fallback={<p>統計退路</p>}><p>AI 建議</p></AIFallback>);
  expect(screen.getByText("AI 建議")).toBeVisible();
  expect(screen.queryByText("統計退路")).not.toBeInTheDocument();
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});

test.each(["unavailable", "invalid_output"] as const)("spec 5.3 %s 是成功降級，提示並呈現呼叫端的退路", aiStatus => {
  const submit = vi.fn();
  render(<AIFallback aiStatus={aiStatus} fallback={<button onClick={submit}>使用原表單</button>}><p>AI 建議</p></AIFallback>);
  expect(screen.getByRole("status")).toHaveTextContent("以下顯示可用內容");
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(screen.queryByText("AI 建議")).not.toBeInTheDocument();
  expect(submit).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "使用原表單" }));
  expect(submit).toHaveBeenCalledTimes(1);
});

test("503 AI_UNAVAILABLE 僅限量表訪談，既有量表與未送出輸入保留，不重新掛載", () => {
  const current = <section><h2>目前量表 v2</h2><label>量表說明<input defaultValue="原版本" /></label></section>;
  const view = render(<RubricInterviewFallback error={null}>{current}</RubricInterviewFallback>);
  const input = screen.getByLabelText("量表說明");
  fireEvent.change(input, { target: { value: "尚未送出" } });
  view.rerender(<RubricInterviewFallback error={new ApiError(503, "AI_UNAVAILABLE", "example")}>{current}</RubricInterviewFallback>);
  expect(screen.getByRole("alert")).toHaveTextContent("目前量表版本維持不變");
  expect(screen.getByText("目前量表 v2")).toBeVisible();
  expect(screen.getByLabelText("量表說明")).toBe(input);
  expect(input).toHaveValue("尚未送出");
  view.rerender(<RubricInterviewFallback error={null}>{current}</RubricInterviewFallback>);
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(screen.getByLabelText("量表說明")).toHaveValue("尚未送出");
});

test.each([[500, "AI_UNAVAILABLE"], [503, "HTTP_ERROR"]] as const)("%i %s 不誤當量表訪談的 503 降級", (status, code) => {
  render(<RubricInterviewFallback error={new ApiError(status, code, "範例錯誤")}><p>目前版本</p></RubricInterviewFallback>);
  expect(screen.getByRole("alert")).toBeVisible();
  expect(screen.getByRole("alert")).not.toHaveTextContent("目前量表版本維持不變");
  expect(screen.getByText("目前版本")).toBeVisible();
});
