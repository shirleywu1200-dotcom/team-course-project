import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { vi } from "vitest";

import { goalFixtures, goalReportFixtures } from "../../test/goalFixtures";
import { keys } from "../../api/queryKeys";
import { API, renderWithClient, server } from "../../test/server";
import { GoalReportArea } from "./GoalReportArea";

const reportUrl = `${API}/goals/1/report`;
const missing = () => HttpResponse.json({ error: { code: "NOT_FOUND", message: "尚未產生",
  details: { goal_id: 1 } } }, { status: 404 });
const open = () => renderWithClient(<GoalReportArea goalId={1} goalTitle="練習規格分析" />);

beforeEach(() => server.use(http.get(`${API}/goals/1/stats`, () => HttpResponse.json(goalFixtures.insufficient))));

test("L1：404 是尚未產生；不顯示錯誤、不自動產稿或無限重讀", async () => {
  let gets = 0; let posts = 0;
  server.use(http.get(reportUrl, () => { gets++; return missing(); }),
    http.post(`${reportUrl}/draft`, () => { posts++; return HttpResponse.json(goalReportFixtures.ready); }));
  open();
  expect(await screen.findByText("尚未產生回報")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "產生初稿" })).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(gets).toBeLessThanOrEqual(2);
  expect(posts).toBe(0);
});

test("L1：GET 真錯誤顯示 ErrorBanner，請求數至多 2", async () => {
  let gets = 0;
  server.use(http.get(reportUrl, () => { gets++; return HttpResponse.json({ error: {
    code: "INTERNAL_ERROR", message: "讀取失敗", details: {},
  } }, { status: 500 }); }));
  open();
  expect(await screen.findByRole("alert")).toHaveTextContent("讀取失敗");
  expect(gets).toBeLessThanOrEqual(2);
});

test("POST draft 不帶 body；成功只顯示 AI 初稿，人工版仍是使用者文字", async () => {
  let posts = 0; let body = "not-called";
  server.use(http.get(reportUrl, missing), http.post(`${reportUrl}/draft`, async ({ request }) => {
    posts++; body = await request.text(); return HttpResponse.json(goalReportFixtures.ready);
  }));
  const user = userEvent.setup();
  open();
  await user.click(await screen.findByRole("button", { name: "產生初稿" }));
  expect(await screen.findByText("AI 目標初稿")).toBeInTheDocument();
  expect(screen.getByLabelText("人工版")).toHaveValue("使用者人工版");
  expect(body).toBe("");
  expect(posts).toBe(1);
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("AI unavailable 與 invalid_output 都走 200 統計退路，重產不覆寫未存人工版", async () => {
  let gets = 0; let stats = 0;
  server.use(http.get(reportUrl, () => { gets++; return HttpResponse.json(goalReportFixtures.ready); }),
    http.get(`${API}/goals/1/stats`, () => { stats++; return HttpResponse.json(goalFixtures.insufficient); }),
    http.post(`${reportUrl}/draft`, () => HttpResponse.json(goalReportFixtures.unavailable)));
  const user = userEvent.setup();
  open();
  expect(await screen.findByText("AI 目標初稿")).toBeInTheDocument();
  await user.clear(screen.getByLabelText("人工版"));
  await user.type(screen.getByLabelText("人工版"), "還沒儲存的人工內容");
  await user.click(screen.getByRole("button", { name: "重新產生初稿" }));
  expect(await screen.findByText("AI 暫時無法使用，以下顯示可用內容。")).toBeInTheDocument();
  expect(screen.queryByText("AI 目標初稿")).not.toBeInTheDocument();
  expect(screen.getByLabelText("人工版")).toHaveValue("還沒儲存的人工內容");
  expect(await screen.findByRole("region", { name: "目標統計" })).toBeInTheDocument();
  expect(stats).toBeGreaterThan(0);
  expect(gets).toBe(1);
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  server.use(http.post(`${reportUrl}/draft`, () => HttpResponse.json(goalReportFixtures.invalidOutput)));
  await user.click(screen.getByRole("button", { name: "重新產生初稿" }));
  expect(await screen.findByText("AI 回傳內容未通過檢查，以下顯示可用內容。")).toBeInTheDocument();
});

test("validated=false 即使夾帶 draft 也不進 DOM，改讀伺服器統計", async () => {
  let stats = 0;
  server.use(http.get(reportUrl, () => HttpResponse.json({ ...goalReportFixtures.ready,
    validated: false, draft: "不可展示的草稿" })),
  http.get(`${API}/goals/1/stats`, () => { stats++; return HttpResponse.json(goalFixtures.insufficient); }));
  open();
  expect(await screen.findByText("初稿未通過統計核對，以下顯示目標統計。")).toBeInTheDocument();
  expect(screen.queryByText("不可展示的草稿")).not.toBeInTheDocument();
  expect(await screen.findByText("樣本 3 筆，不到 5 筆，只顯示不下結論")).toBeInTheDocument();
  expect(stats).toBeGreaterThan(0);
});

test("人工版先建立但 AI 尚未產生時，不誤稱初稿核對失敗", async () => {
  server.use(http.get(reportUrl, () => HttpResponse.json(goalReportFixtures.manualOnly)));
  open();
  expect(await screen.findByText("尚未產生 AI 初稿。")).toBeInTheDocument();
  expect(screen.queryByText("初稿未通過統計核對，以下顯示目標統計。")).not.toBeInTheDocument();
  expect(screen.getByLabelText("人工版")).toHaveValue("使用者人工版");
});

test("關聯變更後重讀期間不露舊 AI；新回應 validated=false 即改統計退路", async () => {
  let gets = 0;
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  server.use(http.get(reportUrl, async () => {
    gets++;
    if (gets === 1) return HttpResponse.json(goalReportFixtures.ready);
    await held;
    return HttpResponse.json({ ...goalReportFixtures.ready, draft: null, validated: false });
  }));
  const { client } = open();
  expect(await screen.findByText("AI 目標初稿")).toBeInTheDocument();
  void client.invalidateQueries({ queryKey: keys.goalReport(1) });
  expect(await screen.findByText("讀取最新目標回報中…")).toBeInTheDocument();
  expect(screen.queryByText("AI 目標初稿")).not.toBeInTheDocument();
  release();
  expect(await screen.findByText("初稿未通過統計核對，以下顯示目標統計。")).toBeInTheDocument();
  expect(gets).toBe(2);
});

test("PUT manual 只送 manual_text、不帶版本；成功後人工版與 AI 草稿仍分開", async () => {
  const bodies: unknown[] = [];
  server.use(http.get(reportUrl, () => HttpResponse.json(goalReportFixtures.ready)),
    http.put(`${reportUrl}/manual`, async ({ request }) => { bodies.push(await request.json());
      return HttpResponse.json({ ...goalReportFixtures.ready, manual_text: "新人工版" }); }));
  const user = userEvent.setup();
  open();
  await screen.findByText("AI 目標初稿");
  await user.clear(screen.getByLabelText("人工版"));
  await user.type(screen.getByLabelText("人工版"), "新人工版");
  await user.click(screen.getByRole("button", { name: "儲存人工版" }));
  await waitFor(() => expect(bodies).toEqual([{ manual_text: "新人工版" }]));
  expect(await screen.findByText("已儲存人工版")).toBeInTheDocument();
  expect(screen.getByLabelText("人工版")).toHaveValue("新人工版");
  expect(screen.getByText("AI 目標初稿")).toBeInTheDocument();
});

test("尚無回報列仍可先儲存人工版，後端建立回報列而不產 AI 初稿", async () => {
  let posts = 0;
  server.use(http.get(reportUrl, missing),
    http.post(`${reportUrl}/draft`, () => { posts++; return HttpResponse.json(goalReportFixtures.ready); }),
    http.put(`${reportUrl}/manual`, () => HttpResponse.json(goalReportFixtures.manualOnly)));
  const user = userEvent.setup();
  open();
  await screen.findByText("尚未產生回報");
  await user.type(screen.getByLabelText("人工版"), "使用者人工版");
  await user.click(screen.getByRole("button", { name: "儲存人工版" }));
  expect(await screen.findByText("已儲存人工版")).toBeInTheDocument();
  expect(screen.getByText("尚未產生 AI 初稿。")).toBeInTheDocument();
  expect(posts).toBe(0);
});

test("PUT manual 的 413 顯示字數錯誤並保留輸入", async () => {
  server.use(http.get(reportUrl, () => HttpResponse.json(goalReportFixtures.ready)),
    http.put(`${reportUrl}/manual`, () => HttpResponse.json({ error: {
      code: "PAYLOAD_TOO_LARGE", message: "太長", details: {},
    } }, { status: 413 })));
  const user = userEvent.setup();
  open();
  await screen.findByText("AI 目標初稿");
  await user.clear(screen.getByLabelText("人工版"));
  await user.type(screen.getByLabelText("人工版"), "需要保留的人工內容");
  await user.click(screen.getByRole("button", { name: "儲存人工版" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("人工版超過 20,000 字");
  expect(screen.getByLabelText("人工版")).toHaveValue("需要保留的人工內容");
});

test("複製目前人工版；空白停用；排除數原樣顯示", async () => {
  const user = userEvent.setup();
  const writeText = vi.fn().mockResolvedValue(undefined);
  const previous = Object.getOwnPropertyDescriptor(navigator, "clipboard");
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  try {
    server.use(http.get(reportUrl, () => HttpResponse.json(goalReportFixtures.ready)));
    open();
    expect(await screen.findByText("已排除 2 件私人任務")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("人工版"));
    expect(screen.getByRole("button", { name: "複製" })).toBeDisabled();
    await user.type(screen.getByLabelText("人工版"), "當前人工文字");
    fireEvent.click(screen.getByRole("button", { name: "複製" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledExactlyOnceWith("當前人工文字"));
    expect(await screen.findByText("已複製")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "AI 初稿區" })).queryByText("已複製")).not.toBeInTheDocument();
  } finally {
    if (previous) Object.defineProperty(navigator, "clipboard", previous);
    else Reflect.deleteProperty(navigator, "clipboard");
  }
});
