# 端對端流程（todo 13.1；#90）

真實瀏覽器（本機 Chrome）對真實後端與暫時資料庫跑主流程。AI 一律關閉（`AI_PROVIDER=off`）：結果可重現、不花錢。

## 跑法

前置：`g4-pg` 容器在跑（`docker ps -a | grep g4`）、`env/local.env` 有 `G4_TEST_ADMIN_URL`、`backend/.venv` 與 `frontend/node_modules` 已裝好、本機有 Chrome。

```
cd e2e
npm install
npx playwright test
```

- Playwright 會自己啟動後端與 Vite：`scripts/e2e_server.py` 建暫時資料庫 `g4_e2e`。跑完會關掉兩個服務。
- 每個流程開始前呼叫 `tests/helpers.ts` 的 `resetDb(種子)`：`reset_db.py` 把 `g4_e2e` 清回剛跑完遷移的狀態（含 `0003_seed.sql`）再灌種子，後端不必重啟。它只對 `g4_e2e` 動手；`events`、`rubrics` 的防改觸發器只在該交易內停用。
- 除了流程 1，其餘用 `signIn()` 直接呼叫 API 略過啟用精靈，並在瀏覽器存好 token。
- 流程 4 依真實日期：任務 22 最新預計 11/19，完成日＝今天，週報看本週。
- 8000 或 5173 已經被佔用時會直接失敗，先關掉手動開的走查服務。
- 失敗時看 `npx playwright show-report`（含失敗當下的 trace）。
- 收尾刪掉暫時資料庫：`cd backend && PYTHONUTF8=1 .venv/Scripts/python ../scripts/e2e_server.py --drop`

## 流程

| 檔案 | 流程 | 對應 |
| --- | --- | --- |
| `tests/01-onboarding.spec.ts` | 全新資料庫 → 填 token → 導向 `/setup` → 略過全部用預設 → 工作總覽；已啟用後開 `/setup` 會導回首頁 | 12.11 |
| `tests/02-inbox-confirm.spec.ts` | 收件匣確認延期（補註記）與完成 → 任務詳情與 API 反映結果；註記是另一筆 `annotation` 事件 | 12.8；AC-08、34、39 |
| `tests/03-project-adjust-due.spec.ts` | 專案頁延後我的任務（原因＋註記）→ 不換頁，任務表、甘特更新 → 專案歷程看得到 | 12.1；AC-02、AC-03 的 delta 與 orig_due |
| `tests/04-complete-feedback.spec.ts` | 今日頁完成任務 → 完成回報（缺精力不能存）→ 離開待處理 → 週報退路列入本週完成 | 12.9、12.10；AC-43、50 |

## 範圍

- 目前不進 CI（要另裝瀏覽器與 PostgreSQL，`.github/` 改動另開票）。
- 流程跑出前端或後端的 bug 時，開 issue 給負責人，不在這裡修。
