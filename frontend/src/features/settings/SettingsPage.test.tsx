// 12.11 設定頁的 Dev 元件測試（Vitest＋MSW；SDD D-5(b)～(c)）。

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse } from "msw";

import { apiError, capture, makeSettings, renderWithClient } from "../../test/server";
import { SettingsPage } from "./SettingsPage";

const capturePut = (respond = (body: object) => HttpResponse.json(makeSettings(body))) =>
  capture("put", "/settings", respond);
const bodies = (log: ReturnType<typeof capturePut>) => log.map((c) => c.body);

const nav = () => screen.getByRole("navigation", { name: "設定分類" });
const open = async (user: ReturnType<typeof userEvent.setup>, name: string) =>
  user.click(within(await screen.findByRole("navigation", { name: "設定分類" })).getByRole("button", { name }));

test("6 個分類；預設開「角色與範圍」並顯示目前值", async () => {
  renderWithClient(<SettingsPage />);
  expect(await screen.findByRole("heading", { name: "角色與範圍" })).toBeInTheDocument();
  expect(within(nav()).getAllByRole("button").map((b) => b.textContent))
    .toEqual(["角色與範圍", "收件來源", "星數量表", "目標與精力", "確認節奏", "原文保存"]);
  expect(screen.getByLabelText("專案負責人")).toBeChecked();
  expect(screen.getByRole("button", { name: "儲存" })).toBeDisabled();
});

test("儲存只送這組有改的欄位", async () => {
  const user = userEvent.setup();
  const calls = capturePut();
  renderWithClient(<SettingsPage />);
  await open(user, "確認節奏");
  await user.click(screen.getByLabelText("21:00"));
  await user.click(screen.getByLabelText("10 分鐘"));
  await user.click(screen.getByRole("button", { name: "儲存" }));
  expect(await screen.findByRole("status")).toHaveTextContent("已儲存");
  expect(bodies(calls)).toEqual([{ confirm_time: "21:00", confirm_cap_min: 10 }]);
  expect(screen.getByRole("button", { name: "儲存" })).toBeDisabled();
});

test("還原回到已存值", async () => {
  const user = userEvent.setup();
  renderWithClient(<SettingsPage />);
  await open(user, "原文保存");
  await user.click(screen.getByLabelText("180 天"));
  await user.click(screen.getByRole("button", { name: "還原" }));
  expect(screen.getByLabelText("30 天")).toBeChecked();
});

test("切換分類時有未存修改：取消就留在原組，確認就捨棄", async () => {
  const user = userEvent.setup();
  const ask = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
  renderWithClient(<SettingsPage />);
  await screen.findByRole("heading", { name: "角色與範圍" });
  await user.click(screen.getByLabelText("兩者都有"));

  await open(user, "確認節奏");
  expect(ask).toHaveBeenCalledWith("「角色與範圍」有未存的修改，要捨棄嗎？");
  expect(screen.getByLabelText("兩者都有")).toBeChecked();

  await open(user, "確認節奏");
  expect(screen.getByRole("heading", { name: "確認節奏" })).toBeInTheDocument();
  await open(user, "角色與範圍");
  expect(screen.getByLabelText("專案負責人")).toBeChecked();
  ask.mockRestore();
});

test("目標可停用；精力定義空白時不能儲存", async () => {
  const user = userEvent.setup();
  const calls = capturePut();
  renderWithClient(<SettingsPage />);
  await open(user, "目標與精力");
  await user.click(screen.getByLabelText(/時間配置/));
  await user.clear(screen.getByLabelText("「精力低」指的是"));
  expect(screen.getByRole("button", { name: "儲存" })).toBeDisabled();
  await user.type(screen.getByLabelText("「精力低」指的是"), "零碎時間就能做");
  await user.click(screen.getByRole("button", { name: "儲存" }));
  await screen.findByRole("status");
  expect(bodies(calls)).toEqual([{ goal_types_enabled: ["growth", "expectation"], energy_def_low: "零碎時間就能做" }]);
});

test("量表與收件來源沒有儲存鈕", async () => {
  const user = userEvent.setup();
  renderWithClient(<SettingsPage />);
  await open(user, "星數量表");
  expect(await screen.findByRole("button", { name: "用三個問題訂我自己的量表" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "儲存" })).not.toBeInTheDocument();
  await open(user, "收件來源");
  expect(screen.getByText("本版未開放")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "儲存" })).not.toBeInTheDocument();
});

test("量表草稿進行中切換分類會先詢問；取消就留在量表組", async () => {
  const user = userEvent.setup();
  const ask = vi.spyOn(window, "confirm").mockReturnValue(false);
  renderWithClient(<SettingsPage />);
  await open(user, "星數量表");
  await user.click(await screen.findByRole("button", { name: "用三個問題訂我自己的量表" }));
  await open(user, "確認節奏");
  expect(ask).toHaveBeenCalledWith("「星數量表」的草稿還沒確認，要捨棄嗎？");
  expect(screen.getByRole("button", { name: "產生草稿" })).toBeInTheDocument();
  ask.mockRestore();
});

test("儲存失敗顯示錯誤，修改保留", async () => {
  const user = userEvent.setup();
  capturePut(() => apiError(422, "VALIDATION_ERROR"));
  renderWithClient(<SettingsPage />);
  await open(user, "原文保存");
  await user.click(screen.getByLabelText("90 天"));
  await user.click(screen.getByRole("button", { name: "儲存" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.getByLabelText("90 天")).toBeChecked();
});
