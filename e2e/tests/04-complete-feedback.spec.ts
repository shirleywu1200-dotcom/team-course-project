// 流程 4：今日頁完成任務 → 填完成回報 → 週報列入本週完成（12.9、12.10；AC-43、AC-50）。種子 scripts/e2e_seeds/weekly.sql：
// 任務 22「報名表單上線」最新預計 11/19、進行中，所以今天（真實日期）一定在今日頁的「待處理任務」。
// 完成日＝今天，週報看本週（預設週）；AI 關閉，週報走事件清單退路。
import { expect, test } from "@playwright/test";

import { getTask, resetDb, signIn } from "./helpers";

test("今日頁：完成任務並填回報，任務離開待處理，週報列入本週完成", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/weekly.sql");
  await signIn(page, request);

  await page.goto("/today");
  await expect(page.getByRole("heading", { name: "今日" })).toBeVisible();
  const todo = page.getByRole("region", { name: "可動任務" });
  await todo.getByRole("button", { name: "完成報名表單上線" }).click();

  await page.getByRole("link", { name: "填寫完成回報" }).click();
  await expect(page).toHaveURL(/\/tasks\/22\/feedback$/);
  const form = page.getByRole("form", { name: "完成回報表單" });
  const save = form.getByRole("button", { name: "儲存完成回報" });
  await form.getByLabel("實際達成星數").selectOption("4");
  await expect(save).toBeDisabled(); // AC-43：缺精力不能存
  await form.getByLabel("自評精力").selectOption("mid");
  await save.click();

  await expect(page).toHaveURL(/\/today$/);
  await expect(todo.getByRole("link", { name: "報名表單上線" })).toHaveCount(0);
  const { task } = await getTask(request, 22);
  expect(task.status).toBe("done");

  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "週報" })).toBeVisible();
  await page.getByRole("button", { name: /產生初稿/ }).click();
  // AC-50：AI 不可用時仍回退路內容；本週完成列出剛完成的任務
  const doneList = page.getByRole("region", { name: "本週完成" });
  await expect(doneList).toContainText("報名表單上線");
  await expect(doneList).toContainText(`完成日 ${task.done_date}`);
});
