// 流程 5：匯入專案（12.7；AC-30、AC-31 的 UI 側、AC-32、AC-33）。種子 scripts/e2e_seeds/import.sql：
// 專案 1「行銷活動 Q4」（工作）。表格與 backend/tests/acceptance/test_ac30_import_preview_diagnosis.py 相同：
// 第 2 列缺結束、第 3 列結束早於開始（錯誤）；第 4 列名稱重複、第 5 列缺負責人（注意）。
import { expect, test } from "@playwright/test";

import { getJson, resetDb, signIn } from "./helpers";

const AC30_TABLE = `任務,負責人,開始,結束
需求確認,我,2026-11-16,2026-11-18
畫面設計,小薇,2026-11-17,
API 開發,阿德,2026-11-25,2026-11-20
需求確認,我,2026-11-19,2026-11-21
測試計畫,,2026-11-20,2026-11-24
上線準備,我,2026-11-24,2026-11-26
驗收,阿德,2026-11-26,2026-11-28`;

test("既有專案：診斷兩級、錯誤列沒略過不能保存，略過後保存基準", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/import.sql");
  await signIn(page, request);

  await page.goto("/import");
  await expect(page.getByRole("heading", { name: "匯入專案" })).toBeVisible();
  await page.getByRole("radio", { name: "既有專案" }).check();
  await page.getByLabel("選擇專案").selectOption({ label: "行銷活動 Q4" });
  await page.getByRole("textbox", { name: "貼上表格" }).fill(AC30_TABLE);
  await page.getByRole("button", { name: "預覽" }).click();

  // AC-30：錯誤 2、注意 2、可匯入 5；標準表頭由規則對應，不需要 AI
  const diag = page.getByRole("region", { name: "診斷結果" });
  await expect(diag).toContainText("可匯入 5");
  await expect(diag).toContainText("錯誤 2");
  await expect(diag).toContainText("注意 2");
  await expect(page.getByRole("region", { name: "欄位對應" })).toContainText("規則對應");

  // AC-31 的 UI 側：錯誤列沒略過時不能保存
  const save = page.getByRole("button", { name: "保存基準" });
  await expect(save).toBeDisabled();
  await diag.getByLabel("略過第 2 列").check();
  await expect(save).toBeDisabled();
  await diag.getByLabel("略過第 3 列").check();
  await expect(page.getByRole("region", { name: "保存" })).toContainText("將建立 5 個任務、略過 2 列");
  await save.click();
  await expect(page.getByRole("status").filter({ hasText: "已建立 5 個任務、略過 2 列" })).toBeVisible();

  // AC-32：orig_due＝latest_due＝結束日、star_source＝import_default、1 筆 baseline 事件
  const tasks = (await getJson(request, "/tasks?project_id=1")).items;
  expect(tasks.map((t: any) => [t.title, t.orig_due, t.latest_due, t.star_source])).toEqual(
    expect.arrayContaining([
      ["需求確認", "2026-11-18", "2026-11-18", "import_default"],
      ["需求確認", "2026-11-21", "2026-11-21", "import_default"],
      ["測試計畫", "2026-11-24", "2026-11-24", "import_default"],
      ["上線準備", "2026-11-26", "2026-11-26", "import_default"],
      ["驗收", "2026-11-28", "2026-11-28", "import_default"],
    ]),
  );
  expect(tasks).toHaveLength(5);
  expect(tasks.find((t: any) => t.title === "測試計畫").owner).toBe("我"); // 缺負責人預設為我
  const baseline = await getJson(request, "/events?project_id=1&kind=baseline");
  expect(baseline.total).toBe(1);
});

test("新專案＋非標準表頭：AI 關閉時改手動指定欄位，套用後可保存", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/import.sql");
  await signIn(page, request);

  await page.goto("/import");
  await page.getByRole("radio", { name: "新建專案" }).check();
  await page.getByLabel("新專案名稱").fill("尾牙籌備");
  await page.getByRole("textbox", { name: "貼上表格" }).fill("工作項目,窗口,起,迄\n訂餐廳,我,2026-12-01,2026-12-05\n抽獎品採購,小薇,2026-12-02,2026-12-10");
  await page.getByRole("button", { name: "預覽" }).click();

  // AC-33：規則認不出、AI 不可用 → mapped_by=null，要手動指定；指定前不顯示診斷、不能保存
  const mapping = page.getByRole("region", { name: "欄位對應" });
  await expect(mapping).toContainText("需手動指定");
  await expect(page.getByRole("region", { name: "診斷結果" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "保存基準" })).toBeDisabled();

  await mapping.getByLabel("任務名稱").selectOption({ label: "工作項目" });
  await mapping.getByLabel("負責人").selectOption({ label: "窗口" });
  await mapping.getByLabel("開始").selectOption({ label: "起" });
  await mapping.getByLabel("結束").selectOption({ label: "迄" });
  await mapping.getByRole("button", { name: "套用對應" }).click();

  await expect(page.getByRole("region", { name: "診斷結果" })).toContainText("可匯入 2");
  await page.getByRole("button", { name: "保存基準" }).click();
  await expect(page.getByRole("status").filter({ hasText: "已建立 2 個任務" })).toBeVisible();

  const project = (await getJson(request, "/projects")).items.find((p: any) => p.name === "尾牙籌備");
  const tasks = (await getJson(request, `/tasks?project_id=${project.id}`)).items;
  expect(tasks.map((t: any) => [t.title, t.owner, t.orig_due]).sort()).toEqual([
    ["抽獎品採購", "小薇", "2026-12-10"],
    ["訂餐廳", "我", "2026-12-05"],
  ]);
});
