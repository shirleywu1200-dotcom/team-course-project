// 流程 6：資料控制（12.14；AC-53、AC-28 的畫面側、AC-54 的部分）。種子 scripts/e2e_seeds/inbox.sql：
// 4 則來源原文；候選 22（完成，來源 2「API 介面定義已上傳」）指向任務 3（version 1）。
import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

import { AUTH, getJson, resetDb, signIn } from "./helpers";

test("匯出是合法 JSON；刪除所有原文要勾確認，刪除後任務歷程仍在、只顯示原文已刪除", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/inbox.sql");
  await signIn(page, request);

  // 先確認候選 22，讓任務 3 有一筆帶來源的事件（收件匣 UI 已由流程 2 驗過）
  const r = await request.post("/api/v1/candidates/22/confirm", { headers: AUTH, data: { expected_version: 1 } });
  expect(r.ok(), await r.text()).toBe(true);
  await page.goto("/tasks/3");
  await expect(page.getByText("API 介面定義已上傳")).toBeVisible();

  // AC-54（部分）：下載的檔案是合法 JSON，各表筆數與 counts 一致，ai_runs 每列都沒有 raw_output
  await page.goto("/data-control");
  await expect(page.getByRole("heading", { name: "資料控制" })).toBeVisible();
  const exportSection = page.getByRole("region", { name: "匯出資料" });
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    exportSection.getByRole("button", { name: "下載資料匯出" }).click(),
  ]);
  const dump = JSON.parse(readFileSync(await download.path(), "utf-8"));
  for (const [table, n] of Object.entries(dump.counts)) expect(dump.tables[table], table).toHaveLength(n as number);
  expect(dump.tables.sources).toHaveLength(4);
  for (const run of dump.tables.ai_runs) expect(run).not.toHaveProperty("raw_output");

  // AC-53：沒勾確認不能送出；送出後全部原文清除
  const purge = page.getByRole("region", { name: "刪除所有來源原文" });
  await purge.getByRole("button", { name: "刪除所有來源原文" }).click();
  const confirm = purge.getByRole("button", { name: "確認" });
  await expect(confirm).toBeDisabled();
  await purge.getByLabel("我確認刪除所有來源原文").check();
  await confirm.click();
  await expect(purge.getByRole("status")).toContainText("已清除 4 筆來源原文");

  // AC-28 的畫面側：事件還在，原文改顯示已刪除
  await page.goto("/tasks/3");
  await expect(page.getByText("（原文已依設定刪除）")).toBeVisible();
  await expect(page.getByText("API 介面定義已上傳")).toHaveCount(0);
  const { items } = await getJson(request, "/events?task_id=3"); // source 只在歷程查詢（spec 5.8）
  const sourced = items.filter((e: any) => e.source_id !== null);
  expect(sourced.length).toBeGreaterThan(0);
  for (const e of sourced) expect([e.source.purged, e.source.quote]).toEqual([true, null]);
});
