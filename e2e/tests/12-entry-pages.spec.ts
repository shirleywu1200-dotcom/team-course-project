// 流程 12：專案清單與新增任務（12.15；#127 裁 A；FR-TSK-01、08）。從工作總覽的入口點進去，驗「新使用者從零能自行開始用」。
// 12a、12b 用空庫（只有遷移與 0003_seed）；12c 用 scripts/e2e_seeds/goals.sql（專案 1 工作、專案 2 私人）。
import { expect, test } from "@playwright/test";

import { getJson, getTask, resetDb, signIn } from "./helpers";

test("空庫：從工作總覽進專案清單，看到引導並可前往匯入", async ({ page, request }) => {
  resetDb();
  await signIn(page, request);

  await page.goto("/");
  await page.getByRole("main").getByRole("link", { name: "專案現況" }).click();
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByText("此功能尚未開放")).toHaveCount(0);
  const list = page.getByRole("region", { name: "專案清單" });
  await expect(list).toContainText("還沒有專案");

  await list.getByRole("link", { name: "匯入專案" }).click();
  await expect(page).toHaveURL(/\/import$/);
});

test("空庫：從工作總覽新增單點任務，開始日晚於期限先擋下，建立後今日頁看得到", async ({ page, request }) => {
  resetDb();
  await signIn(page, request);
  const { today } = await getJson(request, "/meta/today");

  await page.goto("/");
  await page.getByRole("main").getByRole("link", { name: "新增任務" }).click();
  await expect(page).toHaveURL(/\/tasks\/new$/);
  await expect(page.getByRole("heading", { name: "新增任務", level: 1 })).toBeVisible();

  await page.getByLabel("任務標題").fill("寄出季度報表");
  await page.getByLabel("預計完成日").fill(today);
  await page.getByLabel("開始日").fill("2099-01-01");
  await page.getByRole("button", { name: "建立任務" }).click();
  // FR-TSK-08：開始日晚於期限要擋，不送出
  await expect(page.getByRole("alert")).toContainText("開始日不可晚於預計完成日");
  await expect(page).toHaveURL(/\/tasks\/new$/);
  expect((await getJson(request, "/tasks")).items).toHaveLength(0);

  await page.getByLabel("開始日").fill("");
  await page.getByRole("button", { name: "建立任務" }).click();

  await expect(page).toHaveURL(/\/today$/);
  const created = page.getByRole("status").filter({ hasText: "已建立任務" });
  await expect(created).toBeVisible();
  const id = Number((await created.textContent())?.match(/#(\d+)/)?.[1]);
  await expect(page.getByRole("region", { name: "可動任務" })).toContainText("寄出季度報表");

  const { task } = await getTask(request, id);
  expect(task.title).toBe("寄出季度報表");
  expect(task.project_id).toBeNull();
  expect(task.owner).toBe("我");
  expect(task.scope).toBe("work");
  expect(task.expected_stars).toBe(3);
  expect(task.latest_due).toBe(today);
});

test("有專案：專案清單列出工作與私人範圍，點下去到該專案現況", async ({ page, request }) => {
  resetDb("scripts/e2e_seeds/goals.sql");
  await signIn(page, request);

  await page.goto("/");
  await page.getByRole("main").getByRole("link", { name: "專案現況" }).click();
  const list = page.getByRole("region", { name: "專案清單" });
  await expect(list.getByRole("link", { name: "數據平台維運，工作範圍" })).toBeVisible();
  await expect(list.getByRole("link", { name: "個人事務，私人範圍" })).toBeVisible();

  await list.getByRole("link", { name: "數據平台維運，工作範圍" }).click();
  await expect(page).toHaveURL(/\/projects\/1$/);
  await expect(page.getByRole("heading", { name: "數據平台維運", level: 1 })).toBeVisible();
});
