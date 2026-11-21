// 流程 11：目標頁（12.12；US-16、AC-46、AC-50；FR-GOL-06、07）。種子 scripts/e2e_seeds/goals.sql，期望值寫在種子檔頭。
// 第一段驗關聯、統計、矩陣；第二段驗回報草稿與人工版，「AI 成功」的畫面靠 goals_report.sql 直接存的列
// （讀取時後端會對目前統計重跑 R3）。設計見 docs/dev-b/13-1-slice4-sdd.md。
import { expect, test, type Locator, type Page } from "@playwright/test";

import { AUTH, getJson, resetDb, signIn } from "./helpers";

const GOAL_A = "學會 SQL 視窗函式";
const PRIVATE_TITLE = "健身課程報名"; // 目標 1 關聯的私人任務 42：只進統計，不能出現在畫面
const SEEDED_DRAFT = "本季已關聯 2 件完成事件，平均實際星數 3.5，逾期 1 件，進度 67%。相關工作：視窗函式練習題。";

async function openReport(page: Page): Promise<Locator> {
  await page.goto("/goals");
  await page.getByRole("button", { name: `查看${GOAL_A}統計` }).click();
  const report = page.getByRole("region", { name: `目標回報：${GOAL_A}` });
  await expect(report).toBeVisible();
  return report;
}

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

test.describe("第二段：目標回報", () => {
  test("AI 關：尚未產生 → 產生初稿走退路並排除私人任務；人工版存了重整還在，重新產生不覆蓋", async ({ page, request }) => {
    const none = await request.get("/api/v1/goals/1/report", { headers: AUTH });
    expect(none.status()).toBe(404);
    expect((await none.json()).error.code).toBe("NOT_FOUND");

    const report = await openReport(page);
    await expect(report.getByText("尚未產生回報")).toBeVisible();
    await report.getByRole("button", { name: "產生初稿", exact: true }).click();

    // AC-50：AI 不可用仍給目標統計；私人任務只計數、不列標題（資安規則 2）
    await expect(report.getByText("AI 暫時無法使用")).toBeVisible();
    await expect(report.getByRole("region", { name: "目標統計" })).toContainText("2 ／ 3 件完成事件");
    await expect(report.getByText("已排除 1 件私人任務")).toBeVisible();
    await expect(page.locator("main")).not.toContainText(PRIVATE_TITLE);

    const manual = report.getByLabel("人工版", { exact: true });
    await manual.fill("本季練了視窗函式，下一步套到報表查詢。");
    await report.getByRole("button", { name: "儲存人工版" }).click();
    await expect(report.getByText("已儲存人工版")).toBeVisible();

    const reopened = await openReport(page);
    await expect(reopened.getByLabel("人工版", { exact: true })).toHaveValue("本季練了視窗函式，下一步套到報表查詢。");

    // 比照 AC-51：重新產生初稿，人工版不被覆蓋（畫面與 API 都看）
    const regenerated = page.waitForResponse((r) => r.url().endsWith("/goals/1/report/draft") && r.ok());
    await reopened.getByRole("button", { name: "重新產生初稿" }).click();
    await regenerated;
    await expect(reopened.getByLabel("人工版", { exact: true })).toHaveValue("本季練了視窗函式，下一步套到報表查詢。");
    expect(await getJson(request, "/goals/1/report")).toMatchObject({
      ai_status: "unavailable", validated: false, draft: null, excluded_private: 1,
      manual_text: "本季練了視窗函式，下一步套到報表查詢。" });
  });

  test("已存初稿對得上目前統計：AI 初稿與人工版並列", async ({ page, request }) => {
    resetDb("scripts/e2e_seeds/goals.sql", "scripts/e2e_seeds/goals_report.sql"); // 重灌會清掉啟用狀態，再略過一次
    await signIn(page, request);
    expect(await getJson(request, "/goals/1/report")).toMatchObject({ validated: true, draft: SEEDED_DRAFT });

    const report = await openReport(page);
    await expect(report.getByLabel("AI 初稿", { exact: true })).toHaveText(SEEDED_DRAFT);
    await expect(report.getByLabel("人工版", { exact: true })).toHaveValue("");
    await expect(report.getByText("初稿未通過統計核對")).toHaveCount(0);
    await expect(page.locator("main")).not.toContainText(PRIVATE_TITLE);
  });

  test("FR-GOL-07：新增關聯後統計變了，存下的初稿對不上 → 改顯示統計表", async ({ page, request }) => {
    resetDb("scripts/e2e_seeds/goals.sql", "scripts/e2e_seeds/goals_report.sql"); // 重灌會清掉啟用狀態，再略過一次
    await signIn(page, request);
    expect((await getJson(request, "/goals/1/report")).validated).toBe(true);

    const report = await openReport(page);
    await expect(report.getByLabel("AI 初稿", { exact: true })).toHaveText(SEEDED_DRAFT);

    const inbox = page.getByRole("region", { name: "待關聯任務" });
    await inbox.getByLabel("報表查詢改寫的關聯目標").selectOption({ label: GOAL_A });
    await inbox.getByRole("button", { name: "確認報表查詢改寫關聯" }).click();
    await expect(inbox.getByLabel("報表查詢改寫的關聯目標")).toHaveCount(0);

    // linked 2 → 3：figures 的 linked=2 對不上，讀取時重跑 R3 判 false，草稿不再回傳
    expect(await getJson(request, "/goals/1/report")).toMatchObject({ validated: false, draft: null });
    await expect(report.getByText("初稿未通過統計核對，以下顯示目標統計。")).toBeVisible();
    await expect(report.getByLabel("AI 初稿", { exact: true })).toHaveCount(0);
    await expect(report.getByRole("region", { name: "目標統計" })).toContainText("3 ／ 3 件完成事件");
  });
});
