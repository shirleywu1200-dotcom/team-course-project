// 流程共用：重設暫時資料庫（reset_db.py）、以已啟用的使用者身分開啟 app。
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import type { APIRequestContext, Page } from "@playwright/test";

import { TOKEN } from "../playwright.config";

const ROOT = resolve(import.meta.dirname, "../..");
const PYTHON = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";
export const AUTH = { Authorization: `Bearer ${TOKEN}` };

/** 清回剛跑完遷移的狀態並依序灌種子；種子路徑相對於 repo 根目錄。 */
export function resetDb(...seeds: string[]): void {
  const args = [resolve(ROOT, "e2e/reset_db.py"), ...seeds.map((seed) => resolve(ROOT, seed))];
  execFileSync(resolve(ROOT, "backend", PYTHON), args, {
    cwd: resolve(ROOT, "backend"),
    env: { ...process.env, PYTHONUTF8: "1" },
    stdio: "pipe",
  });
}

/** 略過啟用精靈（流程 1 已驗過這段 UI），並讓瀏覽器帶好 token。 */
export async function signIn(page: Page, request: APIRequestContext): Promise<void> {
  const r = await request.post("/api/v1/settings/onboarding/complete", { headers: AUTH, data: { skipped: true } });
  if (!r.ok()) throw new Error(`略過啟用失敗：${r.status()}`);
  await page.addInitScript((t) => localStorage.setItem("g4.token", t), TOKEN);
}

/** GET /tasks/{id} 回 { task, events }。 */
export async function getTask(request: APIRequestContext, id: number): Promise<{ task: any; events: any[] }> {
  return getJson(request, `/tasks/${id}`);
}

export async function getJson(request: APIRequestContext, path: string): Promise<any> {
  const r = await request.get(`/api/v1${path}`, { headers: AUTH });
  if (!r.ok()) throw new Error(`GET ${path}：${r.status()}`);
  return r.json();
}
