import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { App } from "../App";
import { API, makeSettings, server } from "../test/server";
import { ONBOARDING_PATH } from "../features/settings/OnboardingGate";

beforeEach(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({ matches: false, media: query,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  localStorage.setItem("g4.token", "test-token");
});
afterEach(() => { localStorage.removeItem("g4.token"); window.history.replaceState({}, "", "/"); vi.unstubAllGlobals(); });

function openApp(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

test("M1：啟用精靈的唯一 canonical path 是 /setup", () => {
  expect(ONBOARDING_PATH).toBe("/setup");
});

test("M1：真實 App 根節點會守門，未啟用者由 /import 導向 /setup；略過後回首頁", async () => {
  const user = userEvent.setup();
  let settings = makeSettings({ onboarded_at: null });
  server.use(http.get(`${API}/settings`, () => HttpResponse.json(settings)),
    http.post(`${API}/settings/onboarding/complete`, async ({ request }) => {
      expect(await request.json()).toEqual({ skipped: true });
      settings = makeSettings();
      return HttpResponse.json(settings);
    }));
  openApp("/import");
  expect(await screen.findByRole("heading", { name: "開始設定" })).toBeVisible();
  expect(window.location.pathname).toBe("/setup");
  await user.click(screen.getByRole("button", { name: "略過，全部用預設" }));
  expect(await screen.findByRole("heading", { name: "工作總覽" })).toBeVisible();
  expect(window.location.pathname).toBe("/");
});

test("M1：已啟用者開 /setup 回首頁，不再進精靈", async () => {
  openApp("/setup");
  expect(await screen.findByRole("heading", { name: "工作總覽" })).toBeVisible();
  await waitFor(() => expect(window.location.pathname).toBe("/"));
});

test.each([["/import", "匯入專案"], ["/inbox", "收件匣"], ["/settings", "設定"]])(
  "M1：已啟用時 App 的 %s 載入 Dev-B 正式頁", async (path, heading) => {
    server.use(http.get(`${API}/projects`, () => HttpResponse.json({ items: [], total: 0 })));
    openApp(path);
    expect(await screen.findByRole("heading", { name: heading, level: 1 })).toBeVisible();
    expect(screen.queryByText("此功能尚未開放。")).not.toBeInTheDocument();
  },
);
