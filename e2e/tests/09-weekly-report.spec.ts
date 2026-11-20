// 流程 9：週報（12.13；AC-48 畫面側、AC-49、AC-50、AC-51）。種子 scripts/e2e_seeds/weekly.sql：
// 11/09 週完成 11、12，任務 13 延期，私人任務 31「牙醫回診」本週完成但要被排除；weekly_report.sql 另加兩列已存的週報。
// AI 關閉：產生初稿走退路；「AI 成功」的畫面靠 weekly_report.sql 直接存的列（讀取時後端會重新對帳）。
import { expect, test } from "@playwright/test";

import { getJson, resetDb, signIn } from "./helpers";

const WEEK = "2026-11-09";

test("AI 關：產生初稿走退路並排除私人任務；人工版存了重整還在，重新產生不覆蓋", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/weekly.sql");
  await signIn(page, request);

  await page.goto(`/reports?week_start=${WEEK}`);
  await expect(page.getByRole("heading", { name: "週報", level: 1 })).toBeVisible();
  await expect(page.getByText("本週尚未產生週報")).toBeVisible();
  await page.getByRole("button", { name: "產生初稿", exact: true }).click();

  // AC-50：AI 不可用仍給事件清單；AC-48：私人任務只計數、不出現
  await expect(page.getByText("AI 暫時無法使用")).toBeVisible();
  const done = page.getByRole("region", { name: "本週完成" });
  await expect(done).toContainText("場地合約簽回");
  await expect(done).toContainText("贊助商名單確認");
  await expect(page.getByRole("region", { name: "延期事項" })).toContainText("邀請函設計");
  await expect(page.getByText("產生當下排除 1 項私人任務。")).toBeVisible();
  await expect(page.locator("main")).not.toContainText("牙醫回診");

  const manual = page.getByLabel("人工版", { exact: true });
  await manual.fill("本週重點：場地已簽約，邀請函延到 11/14。");
  await page.getByRole("button", { name: "儲存人工版" }).click();
  await expect(page.getByText("已儲存人工版")).toBeVisible();

  await page.reload();
  await expect(manual).toHaveValue("本週重點：場地已簽約，邀請函延到 11/14。");

  // AC-51：重新產生初稿，人工版不被覆蓋（畫面與 API 都看）
  const regenerated = page.waitForResponse((r) => r.url().endsWith("/reports/weekly/draft") && r.ok());
  await page.getByRole("button", { name: "重新產生初稿" }).click();
  await regenerated;
  await expect(manual).toHaveValue("本週重點：場地已簽約，邀請函延到 11/14。");
  const report = await getJson(request, `/reports/weekly?week_start=${WEEK}`);
  expect(report.manual_text).toBe("本週重點：場地已簽約，邀請函延到 11/14。");
});

test("人工版有未存修改時換週，取消後留在原週、文字還在", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/weekly.sql");
  await signIn(page, request);

  await page.goto(`/reports?week_start=${WEEK}`);
  await page.getByRole("button", { name: "產生初稿", exact: true }).click();
  const manual = page.getByLabel("人工版", { exact: true });
  await manual.fill("還沒存的草稿");

  let message = "";
  page.once("dialog", (dialog) => { message = dialog.message(); void dialog.dismiss(); });
  await page.getByLabel("選擇週次").fill("2026-11-02");
  expect(message).toContain("未儲存的修改");
  await expect(page).toHaveURL(new RegExp(`week_start=${WEEK}`));
  await expect(manual).toHaveValue("還沒存的草稿");
});

test("已存的初稿對得上歷程：初稿與人工版並列，每項可點進任務", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/weekly.sql", "scripts/e2e_seeds/weekly_report.sql");
  await signIn(page, request);
  // 先用 API 確認種子真的對得上，避免種子寫錯卻看起來通過
  expect((await getJson(request, `/reports/weekly?week_start=${WEEK}`)).validated).toBe(true);

  await page.goto(`/reports?week_start=${WEEK}`);
  const ai = page.getByRole("region", { name: "AI 初稿區" });
  await expect(ai.getByLabel("AI 初稿", { exact: true })).toHaveText(
    "本週完成：場地合約簽回。延期：邀請函設計改到 11/14。下週重點：報名表單上線。");
  await expect(page.getByRole("region", { name: "人工版區" }).getByLabel("人工版", { exact: true })).toBeVisible();

  await ai.getByRole("link", { name: "場地合約簽回" }).click();
  await expect(page).toHaveURL(/\/tasks\/11$/);
});

test("AC-49：初稿的延期項在歷程找不到事件，不顯示初稿、改列事件清單", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/weekly.sql", "scripts/e2e_seeds/weekly_report.sql");
  await signIn(page, request);
  expect((await getJson(request, "/reports/weekly?week_start=2026-11-02")).validated).toBe(false);

  await page.goto("/reports?week_start=2026-11-02");
  const ai = page.getByRole("region", { name: "AI 初稿區" });
  await expect(ai.getByText("初稿未通過歷程核對")).toBeVisible();
  await expect(ai).not.toContainText("這段不該顯示");
});
