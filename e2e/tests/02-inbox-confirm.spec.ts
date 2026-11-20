// 流程 2：收件匣確認候選（12.8；AC-34、AC-39）。種子 scripts/e2e_seeds/inbox.sql：
// 任務 2「畫面規格 v1」（負責人我，最新 11/13）有延期候選 → 11/20；任務 3「API 介面定義」有完成候選。
import { expect, test } from "@playwright/test";

import { getTask, resetDb, signIn } from "./helpers";

test("收件匣：確認延期並補註記、確認完成，任務詳情反映結果", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/inbox.sql");
  await signIn(page, request);

  // AC-34：候選還是 open 時，任務維持原值
  expect((await getTask(request, 2)).task.latest_due).toBe("2026-11-13");

  await page.goto("/inbox");
  await expect(page.getByRole("heading", { name: "收件匣" })).toBeVisible();

  const delayCard = page.locator("article", { hasText: "畫面規格 v1" });
  await expect(delayCard.getByLabel("新的預計完成日")).toHaveValue("2026-11-20");
  await delayCard.getByRole("button", { name: "確認" }).click();

  // AC-39：我的任務延期 → 已處理區出現註記表單；三選一不預選
  const decided = page.locator(".done-item", { hasText: "延到 2026-11-20" });
  await expect(decided).toBeVisible();
  await expect(decided.getByLabel("不計入")).not.toBeChecked();
  await decided.getByLabel("不計入").check();
  await decided.getByRole("button", { name: "送出註記" }).click();
  await expect(decided.getByText("已註記")).toBeVisible();

  const doneCard = page.locator("article", { hasText: "API 介面定義" });
  await doneCard.getByRole("button", { name: "確認" }).click();
  await expect(page.locator(".done-item", { hasText: "API 介面定義" })).toContainText("完成");

  // 任務詳情（真實路由 /tasks/:id）看得到確認後的值
  await page.goto("/tasks/2");
  await expect(page.getByRole("heading", { name: "畫面規格 v1", level: 1 })).toBeVisible();
  await expect(page.locator("dd", { hasText: "2026-11-20" }).first()).toBeVisible();
  const { task: t2, events } = await getTask(request, 2);
  expect([t2.orig_due, t2.latest_due]).toEqual(["2026-11-13", "2026-11-20"]);
  // AC-08：註記是新增一筆 annotation 事件指向日期事件，原事件不變
  const due = events.find((e) => e.field === "latest_due");
  expect(due.mark).toBeNull();
  expect(events.filter((e) => e.kind === "annotation").map((e) => [e.ref_event_id, e.mark])).toEqual([[due.id, "none"]]);

  await page.goto("/tasks/3");
  await expect(page.getByRole("heading", { name: "API 介面定義", level: 1 })).toBeVisible();
  expect((await getTask(request, 3)).task.status).toBe("done");
});
