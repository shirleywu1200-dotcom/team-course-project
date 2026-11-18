import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { App } from "../../App";
import { keys } from "../../api/queryKeys";
import { dataControlFixtures } from "../../test/fixtures";
import { API, makeSettings, renderWithClient, server } from "../../test/server";
import { DataControlPage } from "./DataControlPage";

function open() {
  return renderWithClient(<MemoryRouter initialEntries={["/data-control"]}>
    <Routes><Route path="/data-control" element={<DataControlPage />} /></Routes>
  </MemoryRouter>);
}

test("版面依序是保存期限、匯出資料、刪除原文；初值取 SettingsOut", async () => {
  open();
  await screen.findByRole("combobox", { name: "保存期限" });
  const headings = screen.getAllByRole("heading", { level: 2 }).map(node => node.textContent);
  expect(headings).toEqual(["保存期限", "匯出資料", "刪除所有來源原文"]);
  expect(screen.getByRole("combobox", { name: "保存期限" })).toHaveValue("30");
  expect(screen.getByText(/來源原文與 AI 原始輸出會被清除/)).toBeInTheDocument();
});

test("縮短期限先確認；取消零 PUT，確認後只送 retention_days 並更新完整 settings", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(
    http.get(`${API}/settings`, () => HttpResponse.json(makeSettings({ retention_days: 90 }))),
    http.put(`${API}/settings`, async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json(makeSettings({ retention_days: 30 }));
    }),
  );
  const { client } = open();
  await user.selectOptions(await screen.findByRole("combobox", { name: "保存期限" }), "30");
  await user.click(screen.getByRole("button", { name: "儲存保存期限" }));
  expect(screen.getByRole("heading", { name: "確認縮短保存期限" })).toBeInTheDocument();
  expect(bodies).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "取消" }));
  expect(bodies).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "儲存保存期限" }));
  expect(screen.getByRole("button", { name: "確認" })).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: /可能立即清除/ }));
  await user.click(screen.getByRole("button", { name: "確認" }));
  await waitFor(() => expect(bodies).toEqual([{ retention_days: 30 }]));
  await waitFor(() => expect(client.getQueryData(keys.settings)).toEqual(makeSettings({ retention_days: 30 })));
});

test("延長或不變免確認，按儲存才 PUT", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(http.put(`${API}/settings`, async ({ request }) => {
    bodies.push(await request.json());
    return HttpResponse.json(makeSettings({ retention_days: 90 }));
  }));
  open();
  await user.selectOptions(await screen.findByRole("combobox", { name: "保存期限" }), "90");
  expect(bodies).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "儲存保存期限" }));
  await waitFor(() => expect(bodies).toEqual([{ retention_days: 90 }]));
  expect(screen.queryByRole("heading", { name: "確認縮短保存期限" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "儲存保存期限" }));
  await waitFor(() => expect(bodies).toHaveLength(2));
});

test("POST /export 無 body；空表與零計數仍下載伺服器 JSON，檔名取原時間戳", async () => {
  const user = userEvent.setup();
  const requests: string[] = [];
  const create = vi.fn().mockReturnValue("blob:example");
  const revoke = vi.fn();
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: create });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revoke });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    requests.push(`${this.download}|${this.href}`);
  });
  server.use(http.post(`${API}/export`, async ({ request }) => {
    expect(await request.text()).toBe("");
    return HttpResponse.json(dataControlFixtures.exportEmpty);
  }));
  try {
    open();
    await user.click(screen.getByRole("button", { name: "下載資料匯出" }));
    await waitFor(() => expect(requests).toEqual(["資料匯出-20261116.json|blob:example"]));
    expect(create).toHaveBeenCalledWith(expect.objectContaining({ type: "application/json;charset=utf-8" }));
    expect(revoke).toHaveBeenCalledWith("blob:example");
  } finally { delete (URL as Partial<typeof URL>).createObjectURL; delete (URL as Partial<typeof URL>).revokeObjectURL; click.mockRestore(); }
});

test.each([0, 3])("二次確認後才送 StrictBool；purged=%s 皆成功且清除來源快取", async purged => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(http.post(`${API}/sources/purge`, async ({ request }) => {
    bodies.push(await request.json());
    return HttpResponse.json({ purged });
  }));
  const { client } = open();
  client.setQueryData(keys.candidates("open"), { items: [{ quote: "待清原文" }] });
  client.setQueryData(["events", { task_id: 4 }], { items: [{ source: { quote: "待清原文" } }] });
  await user.click(screen.getByRole("button", { name: "刪除所有來源原文" }));
  expect(bodies).toHaveLength(0);
  expect(screen.getByRole("button", { name: "確認" })).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: /我確認刪除/ }));
  await user.click(screen.getByRole("button", { name: "確認" }));
  await waitFor(() => expect(bodies).toEqual([{ confirm: true }]));
  expect(await screen.findByText(`已清除 ${purged} 筆來源原文。`)).toBeInTheDocument();
  expect(client.getQueryData(keys.candidates("open"))).toBeUndefined();
  expect(client.getQueryData(["events", { task_id: 4 }])).toBeUndefined();
});

test("刪除失敗只顯示錯誤，不重送、不清快取", async () => {
  const user = userEvent.setup();
  let posts = 0;
  server.use(http.post(`${API}/sources/purge`, () => {
    posts++;
    return HttpResponse.json({ error: { code: "INTERNAL_ERROR", message: "清除失敗", details: {} } }, { status: 500 });
  }));
  const { client } = open();
  client.setQueryData(keys.candidates("open"), { items: [{ quote: "仍保留" }] });
  await user.click(screen.getByRole("button", { name: "刪除所有來源原文" }));
  await user.click(screen.getByRole("checkbox", { name: /我確認刪除/ }));
  await user.click(screen.getByRole("button", { name: "確認" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("清除失敗");
  expect(posts).toBe(1);
  expect(client.getQueryData(keys.candidates("open"))).toBeDefined();
});

test.each([404, 401])("L1：真實 App 守門下 settings GET %s 至多兩次", async status => {
  let gets = 0;
  localStorage.setItem("g4.token", "test-token");
  vi.stubGlobal("matchMedia", (media: string) => ({ matches: false, media,
    addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  window.history.replaceState({}, "", "/data-control");
  server.use(http.get(`${API}/settings`, () => {
    gets++;
    return HttpResponse.json({ error: { code: status === 404 ? "NOT_FOUND" : "UNAUTHORIZED", message: "設定讀取失敗", details: {} } }, { status });
  }));
  try {
    render(<App />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await waitFor(() => expect(gets).toBeGreaterThan(0));
    expect(gets).toBeLessThanOrEqual(2);
  } finally {
    localStorage.removeItem("g4.token");
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  }
});

test("刪除來源原文後移除任務快取（任務詳情內嵌的歷程帶原文，不留在記憶體）", async () => {
  const user = userEvent.setup();
  server.use(http.post(`${API}/sources/purge`, () => HttpResponse.json({ purged: 1 })));
  const { client } = open();
  client.setQueryData(keys.task(4), { task: { id: 4 }, events: [{ source: { quote: "待清原文" } }] });
  await user.click(screen.getByRole("button", { name: "刪除所有來源原文" }));
  await user.click(screen.getByRole("checkbox", { name: /我確認刪除/ }));
  await user.click(screen.getByRole("button", { name: "確認" }));
  await screen.findByText("已清除 1 筆來源原文。");
  expect(client.getQueryData(keys.task(4))).toBeUndefined();
});

test("縮短保存期限後移除任務快取（到期原文已被清除）", async () => {
  const user = userEvent.setup();
  server.use(
    http.get(`${API}/settings`, () => HttpResponse.json(makeSettings({ retention_days: 90 }))),
    http.put(`${API}/settings`, () => HttpResponse.json(makeSettings({ retention_days: 30 }))),
  );
  const { client } = open();
  client.setQueryData(keys.task(4), { task: { id: 4 }, events: [{ source: { quote: "到期原文" } }] });
  await user.selectOptions(await screen.findByRole("combobox", { name: "保存期限" }), "30");
  await user.click(screen.getByRole("button", { name: "儲存保存期限" }));
  await user.click(screen.getByRole("checkbox", { name: /可能立即清除/ }));
  await user.click(screen.getByRole("button", { name: "確認" }));
  await waitFor(() => expect(client.getQueryData(keys.settings)).toEqual(makeSettings({ retention_days: 30 })));
  await waitFor(() => expect(client.getQueryData(keys.task(4))).toBeUndefined());
});
