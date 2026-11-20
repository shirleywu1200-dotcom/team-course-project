// 流程 8：基準更正（12.5；AC-20、AC-21 的畫面側、AC-22）。種子 scripts/e2e_seeds/bulk.sql：
// 任務 41「發表簡報定稿」（我的，原訂＝最新 12/10，進行中）。
import { expect, test } from "@playwright/test";

import { getJson, getTask, resetDb, signIn } from "./helpers";

test("任務詳情的小連結：預覽影響不寫入，勾聲明才能更正，只改原訂日並留歷程", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/bulk.sql");
  await signIn(page, request);

  await page.goto("/tasks/41");
  await page.getByRole("button", { name: "原訂日期寫錯了？更正基準" }).click();
  const dialog = page.getByRole("dialog", { name: "基準更正" });
  await dialog.getByLabel("新的原訂日").fill("2026-12-12");

  // 類型與原因不預選，沒選齊不能預覽
  const previewBtn = dialog.getByRole("button", { name: "預覽影響" });
  await expect(previewBtn).toBeDisabled();
  await expect(dialog.getByRole("radio", { checked: true })).toHaveCount(0);
  await dialog.getByRole("radio").first().check();
  await dialog.getByLabel("原因").selectOption({ index: 1 });
  await previewBtn.click();

  // AC-20：顯示影響，資料不變
  await expect(dialog).toContainText("2026-12-10 → 2026-12-12");
  let { task } = await getTask(request, 41);
  expect([task.orig_due, task.latest_due]).toEqual(["2026-12-10", "2026-12-10"]);

  // AC-21 的畫面側：沒勾聲明不能確認
  const commit = dialog.getByRole("button", { name: "確認更正" });
  await expect(commit).toBeDisabled();
  await dialog.getByLabel("我確認這次更正不是為了讓延期看起來比較小").check();
  await commit.click();
  await expect(dialog.getByRole("status")).toContainText("原訂日已更正為 2026-12-12");

  // AC-22：只改 orig_due；新增一筆 baseline 事件，前值 12/10、後值 12/12
  ({ task } = await getTask(request, 41));
  expect([task.orig_due, task.latest_due]).toEqual(["2026-12-12", "2026-12-10"]);
  const { items } = await getJson(request, "/events?task_id=41&kind=baseline");
  expect(items.map((e: any) => [e.from_value, e.to_value])).toEqual([["2026-12-10", "2026-12-12"]]);
});
