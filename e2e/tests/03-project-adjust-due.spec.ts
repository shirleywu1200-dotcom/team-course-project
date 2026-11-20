// 流程 3：專案頁改預計日（12.1、todo 2.x adjust_due；AC-02；AC-03 的 delta 與 orig_due）。種子 scripts/e2e_seeds/weekly.sql：
// 專案 1「年終活動」，任務 22「報名表單上線」（負責人我，原訂＝最新 11/19，進行中）。
import { expect, test } from "@playwright/test";

import { getTask, resetDb, signIn } from "./helpers";

test("專案頁：延後我的任務並註記，任務表、甘特、歷程不換頁就更新", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/weekly.sql");
  await signIn(page, request);

  await page.goto("/projects/1");
  await expect(page.getByRole("heading", { name: "年終活動" })).toBeVisible();
  const row = page.getByRole("row", { name: /報名表單上線/ });
  await expect(row).toContainText("2026-11-19");

  await page.getByRole("button", { name: "改預計日：報名表單上線" }).click();
  const panel = page.getByRole("region", { name: "調整預計完成日" });
  await panel.getByLabel("新的預計完成日").fill("2026-11-26");
  await expect(panel.getByTestId("delta")).toContainText("2026-11-19 → 2026-11-26");
  await panel.getByLabel("原因").selectOption({ index: 1 });

  // AC-02：我的任務沒選註記不能送出；三選一不預選
  const submit = panel.getByRole("button", { name: "確認調整" });
  await expect(submit).toBeDisabled();
  await panel.getByLabel("變差").check();
  await submit.click();

  // 同一頁內（不重新載入）任務表與甘特都換成新日期
  await expect(page.getByRole("region", { name: "調整預計完成日" })).toBeHidden();
  await expect(row).toContainText("2026-11-26");
  await expect(row).toContainText("7 天");
  await expect(page.getByRole("group", { name: /報名表單上線.*延後 7 天/ })).toBeVisible();

  // AC-03 的 delta 與 orig_due 部分（這裡註記用「變差」）：orig_due 不變，事件記下差距與註記
  const { task, events } = await getTask(request, 22);
  expect([task.orig_due, task.latest_due]).toEqual(["2026-11-19", "2026-11-26"]);
  const due = events.find((e) => e.field === "latest_due");
  expect([due.delta_days, due.mark]).toEqual([7, "worse"]);

  await page.getByRole("link", { name: "專案歷程" }).click();
  await expect(page.getByRole("heading", { name: "年終活動歷程" })).toBeVisible();
  await expect(page.getByRole("region", { name: "歷程結果" })).toContainText("報名表單上線");
});
