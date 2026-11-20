// 流程 11：目標頁（12.12；US-16、AC-46）。種子 scripts/e2e_seeds/goals.sql，期望值寫在種子檔頭。
// 第一段只驗關聯、統計、矩陣；回報草稿與人工版等 #111、#115 合併後另開第二段（docs/dev-b/13-1-slice4-sdd.md）。
import { expect, test, type Locator } from "@playwright/test";

import { getJson, resetDb, signIn } from "./helpers";

const GOAL_A = "學會 SQL 視窗函式";

function statValue(stats: Locator, term: string): Locator {
  return stats.locator("dt", { hasText: new RegExp(`^${term}$`) }).locator("xpath=following-sibling::dd[1]");
}

test.beforeEach(async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/goals.sql");
  await signIn(page, request);
});

test("關聯一筆任務到目標，統計與矩陣同步更新；選不關聯的任務離開待關聯清單", async ({ page, request }) => {
  const before = await getJson(request, "/goals/1/stats");
  expect(before.linked).toBe(2);
  expect(before.progress).toEqual({ text: "2 ／ 3 件完成事件", pct: 67 });

  await page.goto("/goals");
  await expect(page.getByRole("heading", { name: "目標與精力", level: 1 })).toBeVisible();
  await page.getByRole("button", { name: `查看${GOAL_A}統計` }).click();
  const stats = page.getByRole("region", { name: "目標統計" });
  await expect(statValue(stats, "關聯事件數")).toHaveText("2");
  await expect(statValue(stats, "進度")).toHaveText("2 ／ 3 件完成事件");

  const inbox = page.getByRole("region", { name: "待關聯任務" });
  await inbox.getByLabel("報表查詢改寫的關聯目標").selectOption({ label: GOAL_A });
  await inbox.getByRole("button", { name: "確認報表查詢改寫關聯" }).click();
  await expect(inbox.getByLabel("報表查詢改寫的關聯目標")).toHaveCount(0);

  const after = await getJson(request, "/goals/1/stats");
  expect(after).toMatchObject({ linked: 3, avg_actual: 4, avg_expected: 3.3, overdue_count: 1,
    energy: { high: 2, mid: 1, low: 0 }, progress: { text: "3 ／ 3 件完成事件", pct: 100 } });
  await expect(statValue(stats, "關聯事件數")).toHaveText("3");
  await expect(statValue(stats, "進度")).toHaveText("3 ／ 3 件完成事件");
  await expect(statValue(stats, "進度比例")).toHaveText("100%");
  await expect(statValue(stats, "平均實際星數")).toHaveText("4");
  await expect(statValue(stats, "平均預設星數")).toHaveText("3.3");

  const row = page.getByRole("region", { name: "目標精力矩陣" }).getByRole("row", { name: new RegExp(GOAL_A) });
  await expect(row.getByRole("cell")).toHaveText(["高", "3", "2", "1", "0"]);

  await inbox.getByLabel("整理會議室的關聯目標").selectOption("none");
  await inbox.getByRole("button", { name: "確認整理會議室關聯" }).click();
  await expect(inbox.getByText("沒有待關聯任務。")).toBeVisible();
  expect((await getJson(request, "/goal-links/pending")).total).toBe(0);

  await page.reload();
  await expect(page.getByRole("region", { name: "待關聯任務" }).getByText("沒有待關聯任務。")).toBeVisible();
});

test("AC-46：樣本不到 5 筆只顯示不下結論；5 筆以上顯示程式判讀", async ({ page, request }) => {
  const small = await getJson(request, "/goals/1/stats");
  expect(small.judgement).toBeNull();
  const enough = await getJson(request, "/goals/2/stats");
  expect(enough).toMatchObject({ linked: 5, judgement: "一致", judgement_note: "主要精力為中，與預期相同" });

  await page.goto("/goals");
  const stats = page.getByRole("region", { name: "目標統計" });
  await page.getByRole("button", { name: `查看${GOAL_A}統計` }).click();
  await expect(stats).toContainText("樣本 2 筆，不到 5 筆，只顯示不下結論");
  await expect(stats.getByText("一致", { exact: true })).toHaveCount(0);

  await page.getByRole("button", { name: "查看帶新人上手統計" }).click();
  await expect(stats.getByRole("heading", { name: "目標統計：帶新人上手" })).toBeVisible();
  await expect(stats.getByText("一致", { exact: true })).toBeVisible();
  await expect(stats).toContainText("主要精力為中，與預期相同");
  const energy = stats.getByLabel("實際精力分布");
  for (const text of ["高：1", "中：3", "低：1"]) await expect(energy.getByText(text, { exact: true })).toBeVisible();
});
