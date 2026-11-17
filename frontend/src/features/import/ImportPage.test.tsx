// 12.7 匯入精靈的 Dev 元件測試（Vitest＋MSW；SDD 第 7 節）。

import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import type { ImportPreview, ImportRow } from "../../api/types";
import { API, apiError, renderWithClient, server } from "../../test/server";
import { ImportPage } from "./ImportPage";

const TEXT = "任務,負責人,開始,結束\n需求確認,我,11/16,11/18";

const row = (index: number, over: Partial<ImportRow> = {}): ImportRow => ({
  index, title: `任務 ${index}`, owner: "我", start: "2026-11-16", end: "2026-11-18", blocking: false, issues: [], ...over,
});
const bad = row(1, { end: null, blocking: true, issues: [{ level: "error", code: "END_MISSING", message: "缺結束日" }] });

function previewOf(rows: ImportRow[], mapped_by: ImportPreview["column_map"]["mapped_by"] = "rule", over = {}): ImportPreview {
  const blocking = rows.filter((r) => r.blocking).length;
  return {
    ai_status: "ok",
    header: ["任務", "負責人", "開始", "結束"],
    column_map: mapped_by === null ? { title: null, owner: null, start: null, end: null, mapped_by }
      : { title: 0, owner: 1, start: 2, end: 3, mapped_by },
    rows: mapped_by === null ? [] : rows,
    summary: { importable: rows.length - blocking, blocking },
    ...over,
  };
}

function capture(path: string, ...responses: (() => Response)[]) {
  const calls: { body: Record<string, unknown>; key: string | null }[] = [];
  server.use(
    http.post(`${API}${path}`, async ({ request }) => {
      calls.push({ body: (await request.json()) as Record<string, unknown>, key: request.headers.get("Idempotency-Key") });
      return responses[Math.min(calls.length - 1, responses.length - 1)]();
    }),
  );
  return calls;
}

async function pasteAndPreview(user: ReturnType<typeof userEvent.setup>, name = "官網改版") {
  await user.type(screen.getByLabelText("新專案名稱"), name);
  await user.click(screen.getByLabelText("貼上表格"));
  await user.paste(TEXT);
  await user.click(screen.getByRole("button", { name: "預覽" }));
}

const saveButton = () => screen.getByRole("button", { name: "保存基準" });

beforeEach(() => {
  server.use(
    http.get(`${API}/projects`, () =>
      HttpResponse.json({
        items: [
          { id: 3, name: "行銷活動 Q4", scope: "work", archived_at: null },
          { id: 5, name: "家裡裝修", scope: "private", archived_at: null },
        ],
        total: 2,
      }),
    ),
  );
});

// ---------- 目標 ----------

test("預設新建專案；名稱或原文空白時不能預覽", async () => {
  const user = userEvent.setup();
  renderWithClient(<ImportPage />);
  expect(screen.getByLabelText("新建專案")).toBeChecked();
  const btn = screen.getByRole("button", { name: "預覽" });
  expect(btn).toBeDisabled();
  await user.click(screen.getByLabelText("貼上表格"));
  await user.paste(TEXT);
  expect(btn).toBeDisabled();
  await user.type(screen.getByLabelText("新專案名稱"), "官網改版");
  expect(btn).toBeEnabled();
});

test("既有專案清單標出私人範圍不會送 AI，預覽帶專案 id", async () => {
  const user = userEvent.setup();
  const calls = capture("/projects/import/preview", () => HttpResponse.json(previewOf([row(0)])));
  renderWithClient(<ImportPage />);
  await user.click(screen.getByLabelText("既有專案"));
  const select = screen.getByLabelText("選擇專案");
  expect(await within(select).findByRole("option", { name: "家裡裝修（私人・不會送 AI）" })).toBeInTheDocument();
  await user.selectOptions(select, "5");
  await user.click(screen.getByLabelText("貼上表格"));
  await user.paste(TEXT);
  await user.click(screen.getByRole("button", { name: "預覽" }));
  await waitFor(() => expect(calls).toHaveLength(1));
  expect(calls[0].body).toEqual({ text: TEXT, target: 5 });
});

// ---------- 對應 ----------

test("規則對應：不需確認，直接可保存；送出帶 Idempotency-Key 並顯示結果", async () => {
  const user = userEvent.setup();
  capture("/projects/import/preview", () => HttpResponse.json(previewOf([row(0)])));
  const commits = capture("/projects/import/commit", () =>
    HttpResponse.json({ project_id: 9, created: 1, skipped: 0, event_id: 40 }, { status: 201 }),
  );
  renderWithClient(<ImportPage />);
  await pasteAndPreview(user);
  expect(await screen.findByText("任務 0")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "確認對應" })).not.toBeInTheDocument();
  await user.click(saveButton());
  expect(await screen.findByText("已建立 1 個任務、略過 0 列（專案 #9）。")).toBeInTheDocument();
  expect(commits[0].key).toBeTruthy();
  expect(commits[0].body).toEqual({
    target: "new", new_name: "官網改版",
    rows: [{ index: 0, title: "任務 0", owner: "我", start: "2026-11-16", end: "2026-11-18", skip: false }],
  });
});

test("AI 對應：確認前不能保存，按確認後可以", async () => {
  const user = userEvent.setup();
  capture("/projects/import/preview", () => HttpResponse.json(previewOf([row(0)], "ai")));
  renderWithClient(<ImportPage />);
  await pasteAndPreview(user);
  await screen.findByText("任務 0");
  expect(saveButton()).toBeDisabled();
  expect(screen.getByText("請先確認欄位對應")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "確認對應" }));
  expect(saveButton()).toBeEnabled();
});

test("修改對應後重送預覽，帶 column_map（不含 mapped_by）", async () => {
  const user = userEvent.setup();
  const calls = capture(
    "/projects/import/preview",
    () => HttpResponse.json(previewOf([row(0)], "ai")),
    () => HttpResponse.json(previewOf([row(0)], "manual")),
  );
  renderWithClient(<ImportPage />);
  await pasteAndPreview(user);
  await screen.findByText("任務 0");
  await user.selectOptions(screen.getByLabelText("負責人"), "");
  await user.click(screen.getByRole("button", { name: "套用對應" }));
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls[1].body.column_map).toEqual({ title: 0, owner: null, start: 2, end: 3 });
  await waitFor(() => expect(saveButton()).toBeEnabled());
});

test("AI 無法判斷（mapped_by=null）：先手動指定任務名稱與結束才顯示診斷", async () => {
  const user = userEvent.setup();
  const calls = capture(
    "/projects/import/preview",
    () => HttpResponse.json(previewOf([], null, { ai_status: "unavailable" })),
    () => HttpResponse.json(previewOf([row(0)], "manual")),
  );
  renderWithClient(<ImportPage />);
  await pasteAndPreview(user);
  expect(await screen.findByText("AI 無法判斷欄位，請手動指定任務名稱與結束欄位。")).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "診斷結果" })).not.toBeInTheDocument();
  const apply = screen.getByRole("button", { name: "套用對應" });
  expect(apply).toBeDisabled();
  await user.selectOptions(screen.getByLabelText("任務名稱"), "0");
  await user.selectOptions(screen.getByLabelText("結束"), "3");
  await user.click(apply);
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls[1].body.column_map).toEqual({ title: 0, owner: null, start: null, end: 3 });
  expect(await screen.findByRole("region", { name: "診斷結果" })).toBeInTheDocument();
});

// ---------- 診斷與略過 ----------

test("錯誤列要勾略過才能保存，commit 帶 skip", async () => {
  const user = userEvent.setup();
  capture("/projects/import/preview", () => HttpResponse.json(previewOf([row(0), bad])));
  const commits = capture("/projects/import/commit", () =>
    HttpResponse.json({ project_id: 9, created: 1, skipped: 1, event_id: 40 }, { status: 201 }),
  );
  renderWithClient(<ImportPage />);
  await pasteAndPreview(user);
  expect(await screen.findByText("缺結束日")).toBeInTheDocument();
  expect(screen.getByText("還有 1 列錯誤未處理")).toBeInTheDocument();
  expect(saveButton()).toBeDisabled();
  await user.click(screen.getByLabelText("略過第 2 列"));
  await user.click(saveButton());
  await waitFor(() => expect(commits).toHaveLength(1));
  expect((commits[0].body.rows as { skip: boolean }[]).map((r) => r.skip)).toEqual([false, true]);
});

test("改原文後清掉預覽，要重新預覽", async () => {
  const user = userEvent.setup();
  capture("/projects/import/preview", () => HttpResponse.json(previewOf([row(0)])));
  renderWithClient(<ImportPage />);
  await pasteAndPreview(user);
  await screen.findByText("任務 0");
  await user.type(screen.getByLabelText("貼上表格"), "x");
  expect(screen.queryByText("任務 0")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "保存基準" })).not.toBeInTheDocument();
});

// ---------- 錯誤 ----------

test("超過上限顯示 413 訊息", async () => {
  const user = userEvent.setup();
  capture("/projects/import/preview", () => apiError(413, "PAYLOAD_TOO_LARGE"));
  renderWithClient(<ImportPage />);
  await pasteAndPreview(user);
  expect(await screen.findByRole("alert")).toHaveTextContent("匯入最多 500 列、50,000 字");
});

test("commit 422 VALIDATION_ERROR 指出列號並提示重新預覽", async () => {
  const user = userEvent.setup();
  capture("/projects/import/preview", () => HttpResponse.json(previewOf([row(0)])));
  capture("/projects/import/commit", () => apiError(422, "VALIDATION_ERROR", { rows: [0] }));
  renderWithClient(<ImportPage />);
  await pasteAndPreview(user);
  await screen.findByText("任務 0");
  await user.click(saveButton());
  expect(await screen.findByRole("alert")).toHaveTextContent("第 1 列仍有錯誤，請修正原文後重新預覽。");
});
