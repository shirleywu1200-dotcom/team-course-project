// 12.11 啟用精靈與守門的 Dev 元件測試（Vitest＋MSW；SDD D-1、D-2、D-5(a)）。

import { useQuery } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { fetchSettings, keys } from "../../api/queries";
import { API, apiError, capture, type Captured, makeSettings, renderWithClient, server } from "../../test/server";
import { OnboardingGate } from "./OnboardingGate";
import { LEAVE_DRAFT, OnboardingPage } from "./OnboardingPage";
import { QUESTIONS } from "./options";

function record(onboarded = false) {
  const log: Captured[] = [];
  let settings = makeSettings({ onboarded_at: onboarded ? "2026-11-15T09:00:00+08:00" : null });
  server.use(http.get(`${API}/settings`, () => HttpResponse.json(settings)));
  capture("put", "/settings", (body) => HttpResponse.json((settings = { ...settings, ...body })), log);
  capture("post", "/settings/onboarding/complete",
    () => HttpResponse.json((settings = { ...settings, onboarded_at: "2026-11-16T09:00:00+08:00" })), log);
  capture("post", "/rubrics/interview", () => HttpResponse.json({ ai_status: "ok", draft: ["1", "2", "3", "4", "5"] }));
  capture("post", "/rubrics", () => HttpResponse.json({ id: 2, version: 1 }, { status: 201 }), log);
  return log;
}

function renderApp(path: string) {
  return renderWithClient(
    <MemoryRouter initialEntries={[path]}>
      <OnboardingGate>
        <Routes>
          <Route path="/" element={<p>首頁</p>} />
          <Route path="/inbox" element={<p>收件匣頁</p>} />
          <Route path="/setup" element={<OnboardingPage />} />
        </Routes>
      </OnboardingGate>
    </MemoryRouter>,
  );
}

const next = (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole("button", { name: /^(開始|下一步)$/ }));
const stepName = () => screen.getByRole("listitem", { current: "step" }).textContent;
const paths = (log: Captured[]) => log.map((c) => `${c.method} ${c.path}`);

async function toRubricDraft(user: ReturnType<typeof userEvent.setup>) {
  for (let i = 0; i < 3; i++) await next(user);
  await user.click(await screen.findByRole("button", { name: "用三個問題訂我自己的量表" }));
  for (const q of QUESTIONS) await user.click(screen.getByLabelText(q.options[0]));
  await user.click(screen.getByRole("button", { name: "產生草稿" }));
  await screen.findByRole("button", { name: "確認成為 v1" });
}

// ---------- 守門 ----------

test("尚未啟用時，任何頁面都導向精靈", async () => {
  record(false);
  renderApp("/inbox");
  expect(await screen.findByRole("heading", { name: "開始設定" })).toBeInTheDocument();
  expect(screen.queryByText("收件匣頁")).not.toBeInTheDocument();
});

test("已啟用時不攔", async () => {
  record(true);
  renderApp("/inbox");
  expect(await screen.findByText("收件匣頁")).toBeInTheDocument();
});

test("已啟用時開精靈導回首頁", async () => {
  record(true);
  renderApp("/setup");
  expect(await screen.findByText("首頁")).toBeInTheDocument();
});

test("讀設定期間顯示載入中，不先渲染頁面", async () => {
  let release!: () => void;
  server.use(http.get(`${API}/settings`, async () => {
    await new Promise<void>((r) => { release = r; });
    return HttpResponse.json(makeSettings());
  }));
  renderApp("/inbox");
  expect(await screen.findByText("載入中…")).toBeInTheDocument();
  expect(screen.queryByText("收件匣頁")).not.toBeInTheDocument();
  release();
  expect(await screen.findByText("收件匣頁")).toBeInTheDocument();
});

test("讀設定失敗時不攔，交給頁面自己處理", async () => {
  server.use(http.get(`${API}/settings`, () => apiError(401, "UNAUTHORIZED")));
  renderApp("/inbox");
  expect(await screen.findByText("收件匣頁")).toBeInTheDocument();
});

test("讀設定失敗後，頁面自己重讀設定也不會被守門收回（不無限重送）", async () => {
  let calls = 0;
  server.use(http.get(`${API}/settings`, () => { calls++; return apiError(401, "UNAUTHORIZED"); }));
  function PageReadingSettings() {
    const s = useQuery({ queryKey: keys.settings, queryFn: fetchSettings });
    return <p>{s.isError ? "頁面顯示錯誤" : "頁面讀取中"}</p>;
  }
  renderWithClient(
    <MemoryRouter initialEntries={["/inbox"]}>
      <OnboardingGate>
        <Routes><Route path="/inbox" element={<PageReadingSettings />} /></Routes>
      </OnboardingGate>
    </MemoryRouter>,
  );
  expect(await screen.findByText("頁面顯示錯誤")).toBeInTheDocument();
  await new Promise((r) => setTimeout(r, 200));
  expect(screen.getByText("頁面顯示錯誤")).toBeInTheDocument();
  expect(calls).toBeLessThanOrEqual(2);
});

// ---------- 精靈 ----------

test("6 步依序前進與後退", async () => {
  const user = userEvent.setup();
  record(false);
  renderApp("/setup");
  await screen.findByRole("heading", { name: "開始設定" });
  expect(screen.getByRole("button", { name: "上一步" })).toBeDisabled();
  const seen = [stepName()];
  for (let i = 0; i < 5; i++) { await next(user); seen.push(stepName()); }
  expect(seen.map((s) => s?.replace(/^\d+\.\s*/, ""))).toEqual(["歡迎", "角色與範圍", "收件來源", "星數量表", "目標與精力", "確認節奏"]);
  expect(screen.getByRole("button", { name: "完成設定" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "上一步" }));
  expect(stepName()).toContain("目標與精力");
});

test("完成時才寫入：先 PUT 有改的欄位，再 complete，之後回首頁", async () => {
  const user = userEvent.setup();
  const log = record(false);
  renderApp("/setup");
  await screen.findByRole("heading", { name: "開始設定" });
  await next(user);
  await user.click(screen.getByLabelText("兩者都有"));
  for (let i = 0; i < 4; i++) await next(user);
  await user.click(screen.getByLabelText("21:00"));
  expect(log).toHaveLength(0);

  await user.click(screen.getByRole("button", { name: "完成設定" }));
  expect(await screen.findByText("首頁")).toBeInTheDocument();
  expect(log.map(({ method, path, body }) => ({ method, path, body }))).toEqual([
    { method: "PUT", path: "/settings", body: { role: "both", confirm_time: "21:00" } },
    { method: "POST", path: "/settings/onboarding/complete", body: { skipped: false } },
  ]);
});

test("沒改任何欄位就完成時，不送 PUT", async () => {
  const user = userEvent.setup();
  const log = record(false);
  renderApp("/setup");
  await screen.findByRole("heading", { name: "開始設定" });
  for (let i = 0; i < 5; i++) await next(user);
  await user.click(screen.getByRole("button", { name: "完成設定" }));
  await screen.findByText("首頁");
  expect(paths(log)).toEqual(["POST /settings/onboarding/complete"]);
});

test("略過時丟掉已填，只送 complete {skipped:true}", async () => {
  const user = userEvent.setup();
  const log = record(false);
  renderApp("/setup");
  await screen.findByRole("heading", { name: "開始設定" });
  await next(user);
  await user.click(screen.getByLabelText("兩者都有"));
  await user.click(screen.getByRole("button", { name: "略過，全部用預設" }));
  await screen.findByText("首頁");
  expect(log.map((c) => c.body)).toEqual([{ skipped: true }]);
  expect(paths(log)).toEqual(["POST /settings/onboarding/complete"]);
});

test("量表確認當下入庫；之後「略過」改稱「略過其餘設定」並註明不會撤回", async () => {
  const user = userEvent.setup();
  const log = record(false);
  renderApp("/setup");
  await screen.findByRole("heading", { name: "開始設定" });
  await toRubricDraft(user);
  await user.click(screen.getByRole("button", { name: "確認成為 v1" }));

  await waitFor(() => expect(paths(log)).toEqual(["POST /rubrics"]));
  expect(screen.getByRole("button", { name: "略過其餘設定" })).toBeInTheDocument();
  expect(screen.getByText("量表已確認為 v1，略過不會撤回。")).toBeInTheDocument();
});

test("量表草稿未確認就按下一步會先詢問：取消就留在這一步，確定才離開", async () => {
  const user = userEvent.setup();
  const ask = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
  const log = record(false);
  renderApp("/setup");
  await screen.findByRole("heading", { name: "開始設定" });
  await toRubricDraft(user);

  await next(user);
  expect(ask).toHaveBeenCalledWith(LEAVE_DRAFT);
  expect(stepName()).toContain("星數量表");
  expect(screen.getByRole("button", { name: "確認成為 v1" })).toBeInTheDocument();

  await next(user);
  expect(stepName()).toContain("目標與精力");
  expect(log).toHaveLength(0);
  ask.mockRestore();
});

test("沒有草稿時換步不詢問", async () => {
  const user = userEvent.setup();
  const ask = vi.spyOn(window, "confirm");
  record(false);
  renderApp("/setup");
  await screen.findByRole("heading", { name: "開始設定" });
  for (let i = 0; i < 5; i++) await next(user);
  expect(ask).not.toHaveBeenCalled();
  ask.mockRestore();
});

test("精力定義清空時不能完成", async () => {
  const user = userEvent.setup();
  record(false);
  renderApp("/setup");
  await screen.findByRole("heading", { name: "開始設定" });
  for (let i = 0; i < 4; i++) await next(user);
  await user.clear(screen.getByLabelText("「精力高」指的是"));
  await next(user);
  expect(screen.getByRole("button", { name: "完成設定" })).toBeDisabled();
});
