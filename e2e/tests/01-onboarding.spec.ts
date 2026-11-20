// 流程 1：首次啟用（12.11）。全新資料庫 → 填 token → 被導向 /setup → 略過全部用預設 → 進工作總覽；之後不再進精靈。
import { expect, test } from "@playwright/test";

import { TOKEN } from "../playwright.config";
import { resetDb } from "./helpers";

test("首次啟用：略過精靈後進入工作總覽，之後不再回到精靈", async ({ page }) => {
  resetDb();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "設定存取 token" })).toBeVisible();
  await page.getByLabel("後端 G4_API_TOKEN").fill(TOKEN);
  await page.getByRole("button", { name: "儲存" }).click();

  await expect(page).toHaveURL(/\/setup$/);
  await expect(page.getByRole("heading", { name: "開始設定" })).toBeVisible();
  await page.getByRole("button", { name: "略過，全部用預設" }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "工作總覽" })).toBeVisible();

  // 後端確實記下啟用時間
  const settings = await page.request.get("/api/v1/settings", { headers: { Authorization: `Bearer ${TOKEN}` } });
  expect(settings.ok()).toBeTruthy();
  expect((await settings.json()).onboarded_at).not.toBeNull();

  // 已啟用者直接開 /setup 會被導回首頁
  await page.goto("/setup");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "工作總覽" })).toBeVisible();
});
