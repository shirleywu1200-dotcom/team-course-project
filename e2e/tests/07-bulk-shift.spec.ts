// 流程 7：整批順延（12.4；AC-14、AC-15、AC-19）。種子 scripts/e2e_seeds/bulk.sql：
// 專案 1「產品發表會」5 項未完成（41、42 是我的；43～45 是別人的）＋1 項已完成。
import { expect, test } from "@playwright/test";

import { getJson, resetDb, signIn } from "./helpers";

const dues = async (request: any) =>
  Object.fromEntries((await getJson(request, "/tasks?project_id=1")).items.map((t: any) => [t.id, [t.orig_due, t.latest_due]]));

test("勾 4 項順延 3 天：預覽不寫入，確認後同一批次、只有我的任務帶註記", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/bulk.sql");
  await signIn(page, request);
  const before = await dues(request);

  await page.goto("/projects/1");
  await page.getByRole("link", { name: "整批順延" }).click();
  await expect(page.getByRole("heading", { name: "整批順延" })).toBeVisible();

  // 預設全選未完成任務；已完成的不列入。取消「直播設備測試」
  const pick = page.getByRole("region", { name: "選擇任務" });
  await expect(pick).toContainText("已完成的 1 項不列入");
  await expect(pick.getByRole("checkbox")).toHaveCount(5);
  await pick.getByLabel("選擇 直播設備測試").uncheck();
  await pick.getByLabel("天數（負數為提前）").fill("3");
  await pick.getByLabel("原因").selectOption({ index: 1 });
  await pick.getByRole("button", { name: "預覽" }).click();

  // AC-19：預覽不寫入
  const preview = page.getByRole("region", { name: "順延預覽" });
  await expect(preview.getByRole("row")).toHaveCount(5); // 表頭＋4 項
  await expect(preview).toContainText("其中 2 項是你的任務");
  expect(await dues(request)).toEqual(before);

  // 我的任務沒選註記不能確認；註記不預選
  const confirm = preview.getByRole("button", { name: "確認順延" });
  await expect(confirm).toBeDisabled();
  await preview.getByLabel("變差").check();
  await confirm.click();
  await expect(page.getByRole("status")).toContainText("已順延 4 項");

  // AC-14：4 項 latest_due 各 +3、orig_due 不變，未勾的不變
  const after = await dues(request);
  expect(after).toEqual({
    ...before,
    41: ["2026-12-10", "2026-12-13"],
    42: ["2026-12-12", "2026-12-15"],
    43: ["2026-12-14", "2026-12-17"],
    44: ["2026-12-08", "2026-12-11"],
  });

  // AC-14、AC-15：4 筆 due 事件共用 batch_id；註記只在我的任務
  const { items } = await getJson(request, "/events?project_id=1&kind=due");
  expect(items).toHaveLength(4);
  expect(new Set(items.map((e: any) => e.batch_id)).size).toBe(1);
  expect(items[0].batch_id).not.toBeNull();
  const marks = Object.fromEntries(items.map((e: any) => [e.task_id, [e.mine, e.mark, e.delta_days]]));
  expect(marks).toEqual({
    41: [true, "worse", 3],
    42: [true, "worse", 3],
    43: [false, null, 3],
    44: [false, null, 3],
  });
});
