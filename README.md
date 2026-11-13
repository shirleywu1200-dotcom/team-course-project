# 個人大總管 APP（課程作業）

三開發兩 QC 協作專案。規格見 `docs/spec.md`，任務見 `docs/todo.md`。

## 角色與 GitHub 帳號
| 角色 | 負責 | GitHub |
|---|---|---|
| 產品負責人 | 裁定 spec 歧義、待決事項、契約變更 | @shirleywu1200-dotcom |
| Dev-A 核心規則線 | Phase 0–4；前端 12.2、12.4、12.5 | @n731110NK |
| Dev-B 資料進出與 AI 線 | Phase 5–8；前端 12.7、12.8、12.11 | @MoraChen |
| Dev-C 前端與目標週報線 | Phase 9–11；前端其餘頁面 | @shirleywu1200-dotcom |
| QC-1 規則與歷程 | Phase 1–5、10；夾具庫 | （待補） |
| QC-2 資料進出、AI 與前端 | Phase 6–9、11–12；Playwright | @Andpeterpan |

產品負責人與 Dev-C 為同一人。Dev-C 的 PR 由 Dev-B 審查，不得自行核准。

## 合併條件（三項皆須成立）
1. 開發自己的單元測試綠
2. QC 的 AC 驗收測試綠
3. 另一位開發審查通過

## 審查配對
Dev-A 審 Dev-B；Dev-B 審 Dev-C；Dev-C 審 Dev-A。
涉及 `adjust_due` 的 PR，Dev-A 與 Dev-B 互審。

## PR 規則
- 一個 PR 對應 todo 的一組任務（建議不超過半個 Phase）
- 標題寫任務編號與 AC 編號，例如「2.1–2.2 write_event 與樂觀鎖（AC-11）」

## 凍結契約
DDL、錯誤格式與錯誤碼、`write_event`、`adjust_due`、`AIClient`、OpenAPI。
只新增遷移，不改既有欄位語意；新增錯誤碼需產品負責人核可。
