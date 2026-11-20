# 端對端流程（todo 13.1；#90）

真實瀏覽器（本機 Chrome）對真實後端與暫時資料庫跑主流程。AI 一律關閉（`AI_PROVIDER=off`）：結果可重現、不花錢。

## 跑法

前置：`g4-pg` 容器在跑（`docker ps -a | grep g4`）、`env/local.env` 有 `G4_TEST_ADMIN_URL`、`backend/.venv` 與 `frontend/node_modules` 已裝好、本機有 Chrome。

```
cd e2e
npm install
npx playwright test
```

- Playwright 會自己啟動後端與 Vite：`scripts/e2e_server.py` 每次都重建暫時資料庫 `g4_e2e`，所以每次都是乾淨的資料。跑完會關掉兩個服務。
- 8000 或 5173 已經被佔用時會直接失敗，先關掉手動開的走查服務。
- 失敗時看 `npx playwright show-report`（含失敗當下的 trace）。
- 收尾刪掉暫時資料庫：`cd backend && PYTHONUTF8=1 .venv/Scripts/python ../scripts/e2e_server.py --drop`

## 流程

| 檔案 | 流程 | 對應 |
| --- | --- | --- |
| `tests/01-onboarding.spec.ts` | 全新資料庫 → 填 token → 導向 `/setup` → 略過全部用預設 → 工作總覽；已啟用後開 `/setup` 會導回首頁 | 12.11 |

## 範圍

- 目前不進 CI（要另裝瀏覽器與 PostgreSQL，`.github/` 改動另開票）。
- 流程跑出前端或後端的 bug 時，開 issue 給負責人，不在這裡修。
