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
- 流程 9 的已存週報接在 `weekly.sql` 後灌 `weekly_report.sql`（`resetDb` 可接多份種子，依序灌入）。
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
| `tests/05-import.spec.ts` | 既有專案貼 AC-30 表格 → 錯誤列沒略過不能保存 → 略過後保存基準；新專案＋非標準表頭 → AI 關時手動指定欄位 → 保存 | 12.7；AC-30、31（畫面側）、32、33 |
| `tests/06-data-control.spec.ts` | 下載匯出（合法 JSON、無 `raw_output`）→ 刪除所有原文（沒勾確認不能送出）→ 任務歷程改顯示原文已刪除 | 12.14；AC-53、AC-28、AC-54（部分） |
| `tests/07-bulk-shift.spec.ts` | 專案頁進整批順延 → 勾 4 項 → 預覽不寫入 → 統一註記 → 同一批次、註記只在我的任務 | 12.4；AC-14、15、19 |
| `tests/08-baseline.spec.ts` | 任務詳情小連結 → 預覽影響不寫入 → 勾聲明才能更正 → 只改原訂日、留一筆 `baseline` 事件 | 12.5；AC-20、21（畫面側）、22 |
| `tests/09-weekly-report.spec.ts` | AI 關產生初稿走退路、私人任務不出現 → 人工版存了重整還在、重新產生不覆蓋；未存就換週會先確認；已存初稿對得上歷程時與人工版並列，對不上改列事件清單 | 12.13；AC-48（畫面側）、49、50、51 |
| `tests/10-history-filter.spec.ts` | 依專案＋類型篩選、網址重整還原 → 再篩同一批次；篩單點任務進任務詳情；專案歷程頁固定該專案 | 12.6；US-19、AC-05（畫面側） |
| `tests/11-goals.spec.ts` | 目標頁：待關聯任務選目標 → 統計與矩陣同步更新；選不關聯後離開清單；樣本不足與程式判讀；回報：AI 關產生初稿走退路、私人任務不出現 → 人工版存了重整還在、重新產生不覆蓋；已存初稿對得上統計時與人工版並列，新增關聯後對不上改顯示統計表 | 12.12；US-16、AC-46、AC-50、FR-GOL-06、07 |

流程 7、8 用 `scripts/e2e_seeds/bulk.sql`（日期在 12 月）；流程 5 用 `import.sql`，流程 6 用 `inbox.sql`，流程 11 用 `goals.sql`，已存的目標回報接著灌 `goals_report.sql`。

## 範圍

- 目前不進 CI（要另裝瀏覽器與 PostgreSQL，`.github/` 改動另開票）。
- 流程跑出前端或後端的 bug 時，開 issue 給負責人，不在這裡修。
