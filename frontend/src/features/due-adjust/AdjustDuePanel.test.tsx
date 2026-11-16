// 12.2 日期調整與註記流程的 Dev 元件測試（Vitest＋MSW）。

import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { keys } from "../../api/queries";
import type { Task } from "../../api/types";
import { API, apiError, makeTask, renderWithClient, server } from "../../test/server";
import { AdjustDuePanel, VERSION_CHANGED_TEXT } from "./AdjustDuePanel";

// 面板依 taskId 自己載入任務（D2）：用 MSW 提供 GET /tasks/{id}
function renderPanel(task: Task, props: Partial<{ onDone: () => void; onClose: () => void }> = {}) {
  server.use(http.get(`${API}/tasks/${task.id}`, () => HttpResponse.json({ task, events: [] })));
  const onDone = props.onDone ?? vi.fn();
  const onClose = props.onClose ?? vi.fn();
  const view = renderWithClient(<AdjustDuePanel taskId={task.id} onDone={onDone} onClose={onClose} />);
  return { ...view, onDone, onClose };
}

async function setDate(user: ReturnType<typeof userEvent.setup>, value: string) {
  const input = await screen.findByLabelText("新的預計完成日");
  await user.clear(input);
  await user.type(input, value);
}

function captureAdjust(response: () => Response | Promise<Response>) {
  const bodies: unknown[] = [];
  server.use(
    http.post(`${API}/tasks/4/adjust-due`, async ({ request }) => {
      bodies.push(await request.json());
      return response();
    }),
  );
  return bodies;
}

const okResult = (over = {}) =>
  HttpResponse.json({
    task: makeTask({ latest_due: "2026-11-21", version: 2 }),
    event: { id: 9, kind: "due", mark: "worse", reason: "underestimated" },
    warnings: [],
    needs_mark: false,
    ...over,
  });

test("FR-AI-06 防回歸：原因與註記一律不預選", async () => {
  const user = userEvent.setup();
  renderPanel(makeTask());
  await setDate(user, "2026-11-21");
  await screen.findByRole("option", { name: "需求變更（外部）" });
  expect(screen.getByLabelText("原因")).toHaveValue("");
  for (const label of ["變好", "變差", "不計入", "稍後註記"]) {
    expect(screen.getByRole("radio", { name: label })).not.toBeChecked();
  }
  await user.selectOptions(screen.getByLabelText("原因"), "wait_external");
  expect(screen.getByRole("note")).toHaveTextContent("建議選「不計入」");
  for (const label of ["變好", "變差", "不計入", "稍後註記"]) {
    expect(screen.getByRole("radio", { name: label })).not.toBeChecked();
  }
});

test("原因只列出該方向的選項，換方向時清掉已選原因", async () => {
  const user = userEvent.setup();
  renderPanel(makeTask());
  await setDate(user, "2026-11-16");
  await screen.findByRole("option", { name: "提早完成條件達成" });
  expect(screen.queryByRole("option", { name: "估計不準（我低估）" })).not.toBeInTheDocument();
  expect(screen.getByTestId("delta")).toHaveTextContent("提前 2 天");
  await user.selectOptions(screen.getByLabelText("原因"), "finished_early");
  await setDate(user, "2026-11-20");
  expect(screen.getByLabelText("原因")).toHaveValue("");
  expect(screen.getByRole("option", { name: "估計不準（我低估）" })).toBeInTheDocument();
});

test("我的任務：選了原因與註記才能送出，送出內容正確", async () => {
  const user = userEvent.setup();
  const bodies = captureAdjust(() => okResult());
  renderPanel(makeTask());
  await setDate(user, "2026-11-21");
  await screen.findByRole("option", { name: "估計不準（我低估）" });
  const submit = screen.getByRole("button", { name: "確認調整" });
  expect(submit).toBeDisabled();
  await user.selectOptions(screen.getByLabelText("原因"), "underestimated");
  expect(submit).toBeDisabled();
  await user.click(screen.getByRole("radio", { name: "變差" }));
  await user.click(submit);
  await screen.findByRole("status");
  expect(bodies).toEqual([
    { new_due: "2026-11-21", expected_version: 1, reason: "underestimated", note: null, mark: "worse", defer_mark: false },
  ]);
});

test("稍後註記送出 defer_mark，並顯示留待補註記", async () => {
  const user = userEvent.setup();
  const bodies = captureAdjust(() => okResult({ needs_mark: true }));
  renderPanel(makeTask());
  await setDate(user, "2026-11-21");
  await screen.findByRole("option", { name: "估計不準（我低估）" });
  await user.selectOptions(screen.getByLabelText("原因"), "underestimated");
  await user.click(screen.getByRole("radio", { name: "稍後註記" }));
  await user.click(screen.getByRole("button", { name: "確認調整" }));
  expect(await screen.findByRole("status")).toHaveTextContent("註記留待稍後補上");
  expect(bodies[0]).toMatchObject({ mark: null, defer_mark: true });
});

test("別人的任務不詢問註記", async () => {
  const user = userEvent.setup();
  const bodies = captureAdjust(() => okResult());
  renderPanel(makeTask({ owner: "阿德" }));
  await screen.findByLabelText("新的預計完成日");
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  await setDate(user, "2026-11-21");
  await screen.findByRole("option", { name: "等對方或客戶回覆（外部）" });
  await user.selectOptions(screen.getByLabelText("原因"), "wait_external");
  await user.click(screen.getByRole("button", { name: "確認調整" }));
  await screen.findByRole("status");
  expect(bodies[0]).toMatchObject({ mark: null, defer_mark: false });
});

test("STALE_VERSION：顯示重新載入訊息，不自動重送", async () => {
  const user = userEvent.setup();
  const bodies = captureAdjust(() => apiError(409, "STALE_VERSION"));
  renderPanel(makeTask());
  await setDate(user, "2026-11-21");
  await screen.findByRole("option", { name: "估計不準（我低估）" });
  await user.selectOptions(screen.getByLabelText("原因"), "underestimated");
  await user.click(screen.getByRole("radio", { name: "不計入" }));
  await user.click(screen.getByRole("button", { name: "確認調整" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("已重新載入");
  await waitFor(() => expect(bodies).toHaveLength(1));
});

test("新日期等於目前值不能送出；已完成任務不顯示表單", async () => {
  renderPanel(makeTask({ status: "done", done_date: "2026-11-10" }));
  expect(await screen.findByText("已完成的任務不能調整預計完成日。")).toBeInTheDocument();
  expect(screen.queryByLabelText("新的預計完成日")).not.toBeInTheDocument();
});

test("送出成功後呼叫 onDone；按關閉呼叫 onClose", async () => {
  const user = userEvent.setup();
  captureAdjust(() => okResult());
  const { onDone, onClose } = renderPanel(makeTask({ owner: "阿德" }));
  await setDate(user, "2026-11-21");
  await screen.findByRole("option", { name: "等對方或客戶回覆（外部）" });
  await user.selectOptions(screen.getByLabelText("原因"), "wait_external");
  await user.click(screen.getByRole("button", { name: "確認調整" }));
  await screen.findByRole("status");
  expect(onDone).toHaveBeenCalledTimes(1);
  expect(screen.queryByText(VERSION_CHANGED_TEXT)).not.toBeInTheDocument();   // 自己送出造成的版本變化不提示
  await user.click(screen.getByRole("button", { name: "關閉" }));
  expect(onClose).toHaveBeenCalledTimes(1);
});

test("D2 條件 1：面板讀 keys.task(taskId)，與詳情頁共用同一份快取", async () => {
  const { client } = renderPanel(makeTask());
  await screen.findByLabelText("新的預計完成日");
  act(() => client.setQueryData(keys.task(4), makeTask({ latest_due: "2026-11-25", version: 2 })));
  expect(await screen.findByText("2026-11-25")).toBeInTheDocument();
});

test("D2 條件 2：填寫期間任務版本改變，清空輸入並提示，之後以新版本送出", async () => {
  const user = userEvent.setup();
  const bodies = captureAdjust(() => okResult());
  const { client } = renderPanel(makeTask());
  await setDate(user, "2026-11-21");
  await screen.findByRole("option", { name: "估計不準（我低估）" });
  await user.selectOptions(screen.getByLabelText("原因"), "underestimated");
  await user.click(screen.getByRole("radio", { name: "變差" }));

  // 別處（例如 12.3 詳情頁或另一個分頁）改了這個任務
  act(() => client.setQueryData(keys.task(4), makeTask({ latest_due: "2026-11-19", version: 2 })));

  expect(await screen.findByText(VERSION_CHANGED_TEXT)).toBeInTheDocument();
  expect(screen.getByLabelText("新的預計完成日")).toHaveValue("");
  expect(screen.getByLabelText("原因")).toHaveValue("");
  expect(screen.getByRole("radio", { name: "變差" })).not.toBeChecked();
  expect(screen.getByRole("button", { name: "確認調整" })).toBeDisabled();
  expect(bodies).toHaveLength(0);   // 舊輸入沒有被送出

  // 使用者重做：提示消失，送出時帶新版本
  await setDate(user, "2026-11-22");
  expect(screen.queryByText(VERSION_CHANGED_TEXT)).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("原因"), "underestimated");
  await user.click(screen.getByRole("radio", { name: "不計入" }));
  await user.click(screen.getByRole("button", { name: "確認調整" }));
  await screen.findByRole("status");
  expect(bodies[0]).toMatchObject({ new_due: "2026-11-22", expected_version: 2, mark: "none" });
});

test("D2 條件 2：沒有填寫時版本改變，不顯示提示", async () => {
  const { client } = renderPanel(makeTask());
  await screen.findByLabelText("新的預計完成日");
  act(() => client.setQueryData(keys.task(4), makeTask({ latest_due: "2026-11-26", version: 2 })));
  await screen.findByText("2026-11-26");
  expect(screen.queryByText(VERSION_CHANGED_TEXT)).not.toBeInTheDocument();
});

test("STALE_VERSION 後重新載入到新版本：清空輸入，只顯示「資料已更新」提示", async () => {
  const user = userEvent.setup();
  let version = 1;
  server.use(
    http.get(`${API}/tasks/4`, () => HttpResponse.json({ task: makeTask({ version }), events: [] })),
    http.post(`${API}/tasks/4/adjust-due`, () => {
      version = 2;
      return apiError(409, "STALE_VERSION");
    }),
  );
  renderWithClient(<AdjustDuePanel taskId={4} onDone={vi.fn()} onClose={vi.fn()} />);
  await setDate(user, "2026-11-21");
  await screen.findByRole("option", { name: "估計不準（我低估）" });
  await user.selectOptions(screen.getByLabelText("原因"), "underestimated");
  await user.click(screen.getByRole("radio", { name: "不計入" }));
  await user.click(screen.getByRole("button", { name: "確認調整" }));
  expect(await screen.findByText(VERSION_CHANGED_TEXT)).toBeInTheDocument();
  expect(screen.getByLabelText("新的預計完成日")).toHaveValue("");
});
