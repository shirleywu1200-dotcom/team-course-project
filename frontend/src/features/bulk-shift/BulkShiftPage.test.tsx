// 12.4 整批順延的 Dev 元件測試（Vitest＋MSW）。

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { API, apiError, makeTask, renderWithClient, server } from "../../test/server";
import { BulkShift } from "./BulkShiftPage";

const TASKS = [
  makeTask({ id: 1, title: "需求確認", status: "done", done_date: "2026-11-10", version: 3 }),
  makeTask({ id: 2, title: "畫面規格 v1", owner: "阿德", latest_due: "2026-11-13", version: 1 }),
  makeTask({ id: 4, title: "確認驗收條件", version: 1 }),
];

function setup(previewBody = {}, commit: () => Response = () =>
  HttpResponse.json({ batch_id: 7, updated: 2, mine_marked: 1, events: [1, 2] })) {
  const calls: { url: string; body: unknown; key: string | null }[] = [];
  server.use(
    http.get(`${API}/tasks`, () => HttpResponse.json({ items: TASKS, total: TASKS.length })),
    http.post(`${API}/projects/1/bulk-shift/preview`, async ({ request }) => {
      calls.push({ url: "preview", body: await request.json(), key: request.headers.get("Idempotency-Key") });
      return HttpResponse.json({
        items: [
          { task_id: 2, title: "畫面規格 v1", owner: "阿德", from: "2026-11-13", to: "2026-11-16", mine: false, warnings: [] },
          { task_id: 4, title: "確認驗收條件", owner: "我", from: "2026-11-18", to: "2026-11-21", mine: true, warnings: [] },
        ],
        mine_count: 1,
        mark_required: true,
        ...previewBody,
      });
    }),
    http.post(`${API}/projects/1/bulk-shift/commit`, async ({ request }) => {
      calls.push({ url: "commit", body: await request.json(), key: request.headers.get("Idempotency-Key") });
      return commit();
    }),
  );
  return calls;
}

async function fillAndPreview(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("天數（負數為提前）"), "3");
  await screen.findByRole("option", { name: "需求變更（外部）" });
  await user.selectOptions(screen.getByLabelText("原因"), "scope_change_external");
  await user.click(screen.getByRole("button", { name: "預覽" }));
  await screen.findByRole("region", { name: "順延預覽" });
}

test("預設全選未完成任務，已完成任務不列入", async () => {
  setup();
  renderWithClient(<BulkShift projectId={1} />);
  expect(await screen.findByLabelText("選擇 畫面規格 v1")).toBeChecked();
  expect(screen.getByLabelText("選擇 確認驗收條件")).toBeChecked();
  expect(screen.queryByLabelText("選擇 需求確認")).not.toBeInTheDocument();
  expect(screen.getByText("已完成的 1 項不列入。")).toBeInTheDocument();
});

test("預覽後要選統一註記才能確認；確認帶 Idempotency-Key 與版本", async () => {
  const user = userEvent.setup();
  const calls = setup();
  renderWithClient(<BulkShift projectId={1} />);
  await screen.findByLabelText("選擇 畫面規格 v1");
  await fillAndPreview(user);
  const preview = screen.getByRole("region", { name: "順延預覽" });
  expect(within(preview).getByText("2026-11-21")).toBeInTheDocument();
  const confirm = screen.getByRole("button", { name: "確認順延" });
  expect(confirm).toBeDisabled();
  for (const label of ["變好", "變差", "不計入", "稍後註記"]) {
    expect(screen.getByRole("radio", { name: label })).not.toBeChecked();   // FR-AI-06
  }
  expect(screen.getByRole("note")).toHaveTextContent("建議選「不計入」");
  await user.click(screen.getByRole("radio", { name: "不計入" }));
  await user.click(confirm);
  expect(await screen.findByRole("status")).toHaveTextContent("已順延 2 項（批次 #7）");
  const commit = calls.find((c) => c.url === "commit")!;
  expect(commit.key).toBeTruthy();
  expect(commit.body).toEqual({
    items: [{ task_id: 2, expected_version: 1 }, { task_id: 4, expected_version: 1 }],
    days: 3, reason: "scope_change_external", note: null, mark: "none", defer_mark: false,
  });
});

test("取消勾選後要重新預覽", async () => {
  const user = userEvent.setup();
  setup();
  renderWithClient(<BulkShift projectId={1} />);
  await screen.findByLabelText("選擇 畫面規格 v1");
  await fillAndPreview(user);
  await user.click(screen.getByLabelText("選擇 畫面規格 v1"));
  expect(screen.queryByRole("region", { name: "順延預覽" })).not.toBeInTheDocument();
});

test("沒有我的任務時不詢問註記", async () => {
  const user = userEvent.setup();
  const calls = setup({ mine_count: 0, mark_required: false });
  renderWithClient(<BulkShift projectId={1} />);
  await screen.findByLabelText("選擇 畫面規格 v1");
  await fillAndPreview(user);
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "確認順延" }));
  await screen.findByRole("status");
  expect(calls.find((c) => c.url === "commit")!.body).toMatchObject({ mark: null, defer_mark: false });
});

test("STALE_VERSION：清掉預覽並提示重新操作", async () => {
  const user = userEvent.setup();
  setup({}, () => apiError(409, "STALE_VERSION", { tasks: [{ task_id: 4 }] }));
  renderWithClient(<BulkShift projectId={1} />);
  await screen.findByLabelText("選擇 畫面規格 v1");
  await fillAndPreview(user);
  await user.click(screen.getByRole("radio", { name: "稍後註記" }));
  await user.click(screen.getByRole("button", { name: "確認順延" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("已重新載入");
  expect(screen.queryByRole("region", { name: "順延預覽" })).not.toBeInTheDocument();
});

test("天數為 0 或沒選原因時不能預覽", async () => {
  const user = userEvent.setup();
  setup();
  renderWithClient(<BulkShift projectId={1} />);
  await screen.findByLabelText("選擇 畫面規格 v1");
  await user.type(screen.getByLabelText("天數（負數為提前）"), "0");
  expect(screen.getByRole("button", { name: "預覽" })).toBeDisabled();
  expect(screen.getByLabelText("原因")).toBeDisabled();
});
