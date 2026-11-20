// 13.1 前後端接合（#90）：真實瀏覽器對真實後端，AI 關閉。用法見 README.md。
import { defineConfig } from "@playwright/test";

export const TOKEN = "e2e-local-token"; // scripts/e2e_server.py 的本機測試值
// Windows 以 cmd.exe 執行指令，不接受以 ../ 開頭的執行檔路徑，所以在 backend/ 下以相對路徑叫 venv 的 python
const PYTHON = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";

export default defineConfig({
  testDir: "./tests",
  workers: 1, // 所有流程共用同一個暫時資料庫 g4_e2e
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: "chrome", // 用本機已裝的 Chrome，不另外下載瀏覽器
    trace: "retain-on-failure",
  },
  webServer: [
    {
      // 重建 g4_e2e、跑遷移後啟動後端（port 8000）
      command: `${PYTHON} ../scripts/e2e_server.py`,
      cwd: "../backend",
      url: "http://127.0.0.1:8000/api/v1/meta/health",
      env: { PYTHONUTF8: "1", AI_PROVIDER: "off" },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "npx vite --port 5173 --strictPort --host 127.0.0.1",
      cwd: "../frontend",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
