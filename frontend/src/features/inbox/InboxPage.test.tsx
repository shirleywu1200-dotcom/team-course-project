// 12.8 收件匣與每日確認的 Dev 元件測試（Vitest＋MSW；SDD 第 6 節）。

import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import type { Candidate } from "../../api/types";
import { API, apiError, makeCandidate, makeTask, renderWithClient, server } from "../../test/server";
import { InboxPage } from "./InboxPage";

const MARKS = ["變好", "變差", "不計入", "稍後註記"];

function serveOpen(...lists: Candidate[][]) {
  let n = 0;
  server.use(
    http.get(`${API}/candidates`, () => {
      const items = lists[Math.min(n++, lists.length - 1)];
      return HttpResponse.json({ items, total: items.length });
    }),
  );
}

function capture(path: string, response: () => Response) {
  const calls: { body: unknown; key: string | null }[] = [];
  server.use(
    http.post(`${API}${path}`, async ({ request }) => {
      calls.push({ body: await request.json().catch(() => null), key: request.headers.get("Idempotency-Key") });
      return response();
    }),
  );
  return calls;
}

const decided = (c: Candidate, over = {}) =>
  HttpResponse.json({ candidate: { ...c, state: "confirmed" }, ...over });

const zone = (title: string) => screen.getByRole("region", { name: new RegExp(`^${title}`) });

// ---------- 分區與頁首 ----------

test("頁首顯示待確認數與上限，候選依種類分到三區", async () => {
  serveOpen([
    makeCandidate({ id: 1, kind: "delay" }),
    makeCandidate({ id: 2, kind: "unclear", certainty: "to_clarify", note: "這是疑問句", suggest: { kind: "stuck" } }),
    makeCandidate({ id: 3, kind: "unmatched", certainty: "to_match", task: null, quote: "報表處理我來" }),
  ]);
  renderWithClient(<InboxPage />);
  expect(await screen.findByText("待確認 3 項")).toBeInTheDocument();
  expect(await screen.findByText("確認時間上限 5 分鐘")).toBeInTheDocument();
  expect(within(zone("待你確認")).getByText("畫面規格 v1")).toBeInTheDocument();
  expect(within(zone("待釐清")).getByText("這是疑問句")).toBeInTheDocument();
  expect(within(zone("待配對")).getByText("「報表處理我來」")).toBeInTheDocument();
});

test("沒有候選時顯示空狀態", async () => {
  renderWithClient(<InboxPage />);
  expect(await screen.findByText("目前沒有待確認項目。確認前，任何狀態與甘特圖都不會改變。")).toBeInTheDocument();
});

test("原句已清除時顯示「原句已刪除」", async () => {
  serveOpen([makeCandidate({ quote: null })]);
  renderWithClient(<InboxPage />);
  expect(await screen.findByText("原句已刪除")).toBeInTheDocument();
});

// ---------- 確認 ----------

test("確認延期：送出新日期與版本；我的任務接註記，三選一不預選", async () => {
  const user = userEvent.setup();
  const c = makeCandidate();
  serveOpen([c], []);
  const calls = capture("/candidates/21/confirm", () =>
    decided(c, { task: makeTask({ id: 2, latest_due: "2026-11-20" }), event: { id: 9, delta_days: 7 }, needs_mark: true }),
  );
  renderWithClient(<InboxPage />);
  const date = await screen.findByLabelText("新的預計完成日");
  expect(date).toHaveValue("2026-11-18");
  await user.clear(date);
  await user.type(date, "2026-11-20");
  await user.click(screen.getByRole("button", { name: "確認" }));

  const done = await screen.findByRole("region", { name: /^已處理/ });
  expect(calls).toHaveLength(1);
  expect(calls[0].body).toEqual({ new_due: "2026-11-20", expected_version: 1 });
  expect(calls[0].key).toBeTruthy();
  expect(within(done).getByText(/延到 2026-11-20/)).toBeInTheDocument();
  for (const label of MARKS) expect(within(done).getByRole("radio", { name: label })).not.toBeChecked();
  expect(within(done).getByLabelText("原因")).toHaveValue("");
});

test("延期註記：選了才送 annotations；選「稍後註記」不呼叫 API", async () => {
  const user = userEvent.setup();
  const c = makeCandidate();
  serveOpen([c], []);
  capture("/candidates/21/confirm", () => decided(c, { event: { id: 9, delta_days: 5 }, needs_mark: true }));
  const notes = capture("/events/9/annotations", () => HttpResponse.json({ event: { id: 10 } }, { status: 201 }));
  renderWithClient(<InboxPage />);
  await user.click(await screen.findByRole("button", { name: "確認" }));
  const done = await screen.findByRole("region", { name: /^已處理/ });
  const send = within(done).getByRole("button", { name: "送出註記" });
  expect(send).toBeDisabled();
  await user.click(within(done).getByRole("radio", { name: "變差" }));
  await user.selectOptions(within(done).getByLabelText("原因"), "underestimated");
  await user.click(send);
  await within(done).findByText("已註記");
  expect(notes.map((n) => n.body)).toEqual([{ mark: "worse", reason: "underestimated", note: null }]);
});

test("延期註記選「稍後註記」：收起面板，不呼叫 annotations", async () => {
  const user = userEvent.setup();
  const c = makeCandidate();
  serveOpen([c], []);
  capture("/candidates/21/confirm", () => decided(c, { event: { id: 9, delta_days: 5 }, needs_mark: true }));
  const notes = capture("/events/9/annotations", () => HttpResponse.json({}, { status: 201 }));
  renderWithClient(<InboxPage />);
  await user.click(await screen.findByRole("button", { name: "確認" }));
  const done = await screen.findByRole("region", { name: /^已處理/ });
  await user.click(within(done).getByRole("radio", { name: "稍後註記" }));
  await user.click(within(done).getByRole("button", { name: "送出註記" }));
  expect(await within(done).findByText("註記留待稍後補上")).toBeInTheDocument();
  expect(notes).toEqual([]);
});

test("確認完成：提示到今日頁補填完成回報，不呼叫完成回報", async () => {
  const user = userEvent.setup();
  const c = makeCandidate({ kind: "done", proposed: null });
  serveOpen([c], []);
  const calls = capture("/candidates/21/confirm", () => decided(c, { feedback_required: true }));
  renderWithClient(<InboxPage />);
  await user.click(await screen.findByRole("button", { name: "確認" }));
  expect(await screen.findByText("完成回報可到今日頁補填")).toBeInTheDocument();
  expect(calls[0].body).toEqual({ expected_version: 1 });
});

test("待釐清：主要按鈕是忽略；依建議確認走 clarify，建議日期可改", async () => {
  const user = userEvent.setup();
  const c = makeCandidate({ kind: "unclear", certainty: "to_clarify", proposed: null,
    suggest: { kind: "delay", new_due: "2026-11-25" }, note: "含「可能」，先不當作延期" });
  serveOpen([c], []);
  const calls = capture("/candidates/21/clarify", () => decided(c, { needs_mark: false }));
  renderWithClient(<InboxPage />);
  const card = await screen.findByRole("article");
  expect(within(card).getByRole("button", { name: "忽略" })).toHaveClass("primary");
  expect(within(card).getByLabelText("新的預計完成日")).toHaveValue("2026-11-25");
  await user.click(within(card).getByRole("button", { name: "我確認：延期" }));
  await screen.findByRole("region", { name: /^已處理/ });
  expect(calls[0].body).toEqual({ new_due: "2026-11-25", expected_version: 1 });
});

test("待配對：期限不預填，填了才能建立新任務", async () => {
  const user = userEvent.setup();
  const c = makeCandidate({ kind: "unmatched", certainty: "to_match", task: null, proposed: null,
    quote: "報表處理我來", speaker: "小薇" });
  serveOpen([c], []);
  const calls = capture("/candidates/21/create-task", () => decided(c, { task: makeTask({ id: 9 }) }));
  renderWithClient(<InboxPage />);
  const create = await screen.findByRole("button", { name: "建立新任務" });
  expect(screen.getByLabelText("期限")).toHaveValue("");
  expect(screen.getByLabelText("標題")).toHaveValue("報表處理我來");
  expect(create).toBeDisabled();
  await user.type(screen.getByLabelText("期限"), "2026-12-20");
  await user.click(create);
  await screen.findByRole("region", { name: /^已處理/ });
  expect(calls[0].body).toEqual({ title: "報表處理我來", owner: "小薇", due: "2026-12-20" });
});

test("忽略：呼叫 ignore，不帶內容", async () => {
  const user = userEvent.setup();
  const c = makeCandidate({ kind: "stuck", proposed: null });
  serveOpen([c], []);
  const calls = capture("/candidates/21/ignore", () => HttpResponse.json({ candidate: { ...c, state: "ignored" } }));
  renderWithClient(<InboxPage />);
  await user.click(await screen.findByRole("button", { name: "忽略" }));
  const done = await screen.findByRole("region", { name: /^已處理/ });
  expect(within(done).getByText("已忽略")).toBeInTheDocument();
  expect(calls).toHaveLength(1);
});

test("STALE_VERSION：顯示錯誤並重新載入清單，不自動重送", async () => {
  const user = userEvent.setup();
  const c = makeCandidate();
  let loads = 0;
  server.use(http.get(`${API}/candidates`, () => {
    loads += 1;
    return HttpResponse.json({ items: [{ ...c, task: { ...c.task!, version: loads } }], total: 1 });
  }));
  const calls = capture("/candidates/21/confirm", () => apiError(409, "STALE_VERSION"));
  renderWithClient(<InboxPage />);
  await user.click(await screen.findByRole("button", { name: "確認" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("資料已被其他操作更新");
  await waitFor(() => expect(loads).toBe(2));
  expect(calls).toHaveLength(1);
});

// ---------- 貼上與解析 ----------

test("同步解析：顯示統計與無法辨識的行，清空輸入並重新載入候選", async () => {
  const user = userEvent.setup();
  serveOpen([], [makeCandidate()]);
  const calls = capture("/ingest", () => HttpResponse.json({
    mode: "sync", ai_status: "ok", candidates: [makeCandidate()],
    result: { created: 1, skipped: 2, duplicates: 1, unparsed_lines: [3] },
  }));
  renderWithClient(<InboxPage />);
  const box = await screen.findByLabelText("貼上群組對話");
  await user.click(box);
  await user.paste("[10:12] 阿德：畫面規格 v1 確定延到 11/18");
  await user.click(screen.getByRole("button", { name: "解析" }));
  expect(await screen.findByText("新增 1 張候選；略過 2 則；重複 1 則。")).toBeInTheDocument();
  expect(screen.getByText("第 3 行無法辨識，修正後可重新貼上。")).toBeInTheDocument();
  expect(box).toHaveValue("");
  expect(calls[0].body).toEqual({ text: "[10:12] 阿德：畫面規格 v1 確定延到 11/18" });
  expect(await screen.findByText("畫面規格 v1")).toBeInTheDocument();
});

test("AI 不可用：顯示退路訊息", async () => {
  const user = userEvent.setup();
  capture("/ingest", () => HttpResponse.json({
    mode: "sync", ai_status: "unavailable", candidates: [],
    result: { created: 0, skipped: 1, duplicates: 0, unparsed_lines: [] },
  }));
  renderWithClient(<InboxPage />);
  await user.type(await screen.findByLabelText("貼上群組對話"), "x");
  await user.click(screen.getByRole("button", { name: "解析" }));
  expect(await screen.findByText(/AI 解析失敗，這批訊息沒有產生候選/)).toBeInTheDocument();
});

test("超過大小上限：顯示錯誤並保留輸入", async () => {
  const user = userEvent.setup();
  capture("/ingest", () => apiError(413, "PAYLOAD_TOO_LARGE"));
  renderWithClient(<InboxPage />);
  const box = await screen.findByLabelText("貼上群組對話");
  await user.type(box, "很長");
  await user.click(screen.getByRole("button", { name: "解析" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("超過 20,000 字");
  expect(box).toHaveValue("很長");
});

test("背景解析：輪詢到完成後顯示結果並重新載入候選", async () => {
  const user = userEvent.setup();
  serveOpen([], [makeCandidate()]);
  capture("/ingest", () => HttpResponse.json({ mode: "async", job_id: 15, status: "queued" }));
  let polls = 0;
  server.use(http.get(`${API}/ingest/jobs/15`, () => {
    polls += 1;
    return HttpResponse.json(polls < 2
      ? { id: 15, status: "running", attempts: 1, result: null, error: null }
      : { id: 15, status: "succeeded", attempts: 1, error: null,
          result: { created: 1, skipped: 0, duplicates: 0, unparsed_lines: [], ai_status: "ok", candidate_ids: [21] } });
  }));
  renderWithClient(<InboxPage pollMs={10} pollLimitMs={5000} />);
  await user.type(await screen.findByLabelText("貼上群組對話"), "x");
  await user.click(screen.getByRole("button", { name: "解析" }));
  expect(await screen.findByText("新增 1 張候選；略過 0 則；重複 0 則。")).toBeInTheDocument();
  expect(await screen.findByText("畫面規格 v1")).toBeInTheDocument();
  expect(polls).toBe(2);
});

test("背景解析失敗：顯示工作的錯誤訊息", async () => {
  const user = userEvent.setup();
  capture("/ingest", () => HttpResponse.json({ mode: "async", job_id: 15, status: "queued" }));
  server.use(http.get(`${API}/ingest/jobs/15`, () => HttpResponse.json(
    { id: 15, status: "failed", attempts: 3, result: null, error: "AI 解析失敗，可在收件匣手動建立任務" })));
  renderWithClient(<InboxPage pollMs={10} pollLimitMs={5000} />);
  await user.type(await screen.findByLabelText("貼上群組對話"), "x");
  await user.click(screen.getByRole("button", { name: "解析" }));
  expect(await screen.findByText("AI 解析失敗，可在收件匣手動建立任務")).toBeInTheDocument();
});

test("背景解析超過上限：停止輪詢並提示稍後查看", async () => {
  const user = userEvent.setup();
  capture("/ingest", () => HttpResponse.json({ mode: "async", job_id: 15, status: "queued" }));
  let polls = 0;
  server.use(http.get(`${API}/ingest/jobs/15`, () => {
    polls += 1;
    return HttpResponse.json({ id: 15, status: "running", attempts: 1, result: null, error: null });
  }));
  renderWithClient(<InboxPage pollMs={10} pollLimitMs={80} />);
  await user.type(await screen.findByLabelText("貼上群組對話"), "x");
  await user.click(screen.getByRole("button", { name: "解析" }));
  expect(await screen.findByText("仍在處理，稍後回收件匣查看。")).toBeInTheDocument();
  const stopped = polls;
  await new Promise((r) => setTimeout(r, 60));
  expect(polls).toBe(stopped);
});
