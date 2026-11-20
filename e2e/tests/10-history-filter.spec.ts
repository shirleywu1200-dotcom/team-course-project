// 流程 10：歷程篩選（12.6；US-19、AC-05 畫面側）。種子 scripts/e2e_seeds/history.sql：
// 專案 1「年終活動」due 4 筆（其中 3 筆同一批次 #1）＋ status 1 筆；專案 2 due 1 筆；單點任務 5「更新個人履歷」due 1 筆。
import { expect, test } from "@playwright/test";

import { getJson, resetDb, signIn } from "./helpers";

test.beforeEach(async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/history.sql");
  await signIn(page, request);
});

test("依專案與類型篩選，網址可重整還原；再篩同一批次只剩該批事件", async ({ page, request }) => {
  await page.goto("/history");
  const filters = page.getByRole("region", { name: "歷程篩選" });
  await filters.getByLabel("專案").selectOption({ label: "年終活動" });
  await filters.getByLabel("類型").selectOption("due");
  await filters.getByRole("button", { name: "套用" }).click();

  const { total } = await getJson(request, "/events?project_id=1&kind=due");
  expect(total).toBe(4);
  await expect(page.getByText("符合 4 筆歷程")).toBeVisible();
  await expect(page).toHaveURL(/project_id=1/);
  await expect(page).toHaveURL(/kind=due/);

  await page.reload();
  await expect(filters.getByLabel("專案")).toHaveValue("1");
  await expect(filters.getByLabel("類型")).toHaveValue("due");
  await expect(page.getByText("符合 4 筆歷程")).toBeVisible();

  const results = page.getByRole("region", { name: "歷程結果" });
  await results.getByRole("button", { name: "篩選批次 #1" }).first().click();
  await expect(filters.getByLabel("批次編號")).toHaveValue("1");
  await filters.getByRole("button", { name: "套用" }).click();
  await expect(page.getByText("符合 3 筆歷程")).toBeVisible();
  await expect(results.getByRole("listitem")).toHaveCount(3);
  await expect(results.getByRole("button", { name: "下一頁" })).toBeDisabled();
});

test("AC-05：篩「單點任務」只列沒有專案的事件，點任務進到詳情", async ({ page }) => {
  await page.goto("/history");
  const filters = page.getByRole("region", { name: "歷程篩選" });
  await filters.getByLabel("專案").selectOption({ label: "單點任務" });
  await filters.getByRole("button", { name: "套用" }).click();

  await expect(page.getByText("符合 1 筆歷程")).toBeVisible();
  const results = page.getByRole("region", { name: "歷程結果" });
  await expect(results).toContainText("專案：單點任務");
  await results.getByRole("button", { name: "查看任務：更新個人履歷" }).click();
  await expect(page).toHaveURL(/\/tasks\/5$/);
});

test("專案歷程頁固定在該專案：沒有專案選單，只列專案 1 的事件", async ({ page }) => {
  await page.goto("/projects/1/history");
  await expect(page.getByRole("heading", { name: "年終活動歷程", level: 1 })).toBeVisible();
  await expect(page.getByRole("region", { name: "歷程篩選" }).getByLabel("專案")).toHaveCount(0);
  await expect(page.getByText("符合 5 筆歷程")).toBeVisible();
  await expect(page.getByRole("region", { name: "歷程結果" })).not.toContainText("新聞稿撰寫");
});
