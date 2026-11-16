// 12.5 基準更正的 Dev 元件測試（Vitest＋MSW）。

import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { API, apiError, makeTask, renderWithClient, server } from "../../test/server";
import { BaselineCorrectionLink } from "./BaselineCorrection";

const PREVIEW = {
  confirmation_token: "tok-1",
  expires_at: "2026-11-11T10:10:00+08:00",
  impact: {
    orig_due: { from: "2026-11-12", to: "2026-11-14" },
    gap_days: { from: 3, to: 1 },
    project_delayed_count: { from: 2, to: 1 },
    past_due_events_kept: 2,
    old_value_kept_in_history: true,
  },
};

function setup(commit: () => Response = () =>
  HttpResponse.json({ task: makeTask({ id: 3, orig_due: "2026-11-14", version: 5 }),
                      event: { id: 50, kind: "baseline", from_value: "2026-11-12" } })) {
  const calls: { url: string; body: unknown }[] = [];
  server.use(
    http.post(`${API}/tasks/3/baseline-correction/preview`, async ({ request }) => {
      calls.push({ url: "preview", body: await request.json() });
      return HttpResponse.json(PREVIEW);
    }),
    http.post(`${API}/tasks/3/baseline-correction/commit`, async ({ request }) => {
      calls.push({ url: "commit", body: await request.json() });
      return commit();
    }),
  );
  return calls;
}

const TASK = makeTask({ id: 3, title: "API 介面定義", owner: "小薇", orig_due: "2026-11-12", latest_due: "2026-11-15", version: 4 });

async function openAndPreview(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "原訂日期寫錯了？更正基準" }));
  await user.type(screen.getByLabelText("新的原訂日"), "2026-11-14");
  await user.click(await screen.findByRole("radio", { name: "更正錯誤" }));
  await user.selectOptions(screen.getByLabelText("原因"), "plan_date_wrong");
  await user.click(screen.getByRole("button", { name: "預覽影響" }));
  await screen.findByLabelText("更正影響");
}

test("入口是小連結；類型與原因預設不選", async () => {
  const user = userEvent.setup();
  setup();
  renderWithClient(<BaselineCorrectionLink task={TASK} />);
  const link = screen.getByRole("button", { name: "原訂日期寫錯了？更正基準" });
  expect(link).toHaveClass("link-button");
  await user.click(link);
  expect(await screen.findByRole("radio", { name: "更正錯誤" })).not.toBeChecked();
  expect(screen.getByLabelText("原因")).toHaveValue("");
  expect(screen.getByRole("button", { name: "預覽影響" })).toBeDisabled();
});

test("已完成任務不顯示入口", () => {
  renderWithClient(<BaselineCorrectionLink task={makeTask({ status: "done", done_date: "2026-11-10" })} />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

test("兩段式：預覽影響後，勾選聲明才能確認", async () => {
  const user = userEvent.setup();
  const calls = setup();
  renderWithClient(<BaselineCorrectionLink task={TASK} />);
  await openAndPreview(user);
  expect(calls[0].body).toEqual({ new_orig_due: "2026-11-14", type: "correction", reason: "plan_date_wrong", expected_version: 4 });
  expect(screen.getByText("2026-11-12 → 2026-11-14")).toBeInTheDocument();
  expect(screen.getByText("2 筆，保留原樣，不重算")).toBeInTheDocument();
  const confirm = screen.getByRole("button", { name: "確認更正" });
  expect(confirm).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: "我確認這次更正不是為了讓延期看起來比較小" }));
  await user.click(confirm);
  expect(await screen.findByRole("status")).toHaveTextContent("舊值 2026-11-12 已留在歷程");
  expect(calls[1]).toEqual({ url: "commit", body: { confirmation_token: "tok-1", ack: true } });
});

test("CONFIRMATION_INVALID：回到第一步重新預覽", async () => {
  const user = userEvent.setup();
  setup(() => apiError(409, "CONFIRMATION_INVALID"));
  renderWithClient(<BaselineCorrectionLink task={TASK} />);
  await openAndPreview(user);
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: "確認更正" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("請重新預覽");
  expect(screen.queryByLabelText("更正影響")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "預覽影響" })).toBeEnabled();
});

test("改了輸入就要重新預覽", async () => {
  const user = userEvent.setup();
  setup();
  renderWithClient(<BaselineCorrectionLink task={TASK} />);
  await openAndPreview(user);
  await user.selectOptions(screen.getByLabelText("原因"), "input_error");
  expect(screen.queryByLabelText("更正影響")).not.toBeInTheDocument();
});
