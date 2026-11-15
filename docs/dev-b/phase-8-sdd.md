# Phase 8 SDD：設定、量表與資料控制（Dev-B）

依據：spec 3.1（FR-SET-01～04）、3.2（FR-RUB-01～05）、3.17（FR-GOV-01～03、05）、5.4、5.15、6.6、6.7；todo Phase 8（8.1～8.7，8.8 不做）；AC-52～54；decisions DA-23。
狀態：**已定案**（2026-11-15 產品負責人：Q1～Q6 全部依建議；Q1 的精力定義預設文字照第 2 節；Q5 已改寫 spec 6.7）。

## 1. 端點

| Method | Path | 任務 | 說明 |
| --- | --- | --- | --- |
| GET | `/settings` | 8.1 | 取得設定；沒有資料列時先補預設列（Q1） |
| PUT | `/settings` | 8.1 | 部分更新 |
| POST | `/settings/onboarding/complete` | 8.1 | `{ "skipped": bool }`，寫 `onboarded_at` |
| GET | `/rubrics` | 8.2 | `{items, total}`，依版本由舊到新；`?active=true` 時 `items` 只有最新版 |
| POST | `/rubrics/interview` | 8.3 | AI-06：三題 → 5 句草稿；AI 失敗回 503 |
| POST | `/rubrics` | 8.4 | 確認草稿為新版本 |
| POST | `/sources/purge` | 8.6 | 刪除所有來源原文，需 `{ "confirm": true }` |
| POST | `/export` | 8.7 | 回傳 JSON 下載 |

8.5 每日清除不是端點，是背景排程（第 4 節）。8.8 依分工不做。

## 2. 設定（8.1）

- `settings` 是單列表（`id=1`），0001 遷移沒有插入預設列。由 `settings_repo.ensure_defaults` 以 `INSERT … ON CONFLICT (id) DO NOTHING` 補上，讀取設定（`GET /settings`、收件時取保存期限、onboarding）時呼叫；量表 v0 則在讀取量表或確認新版本時補（Q1）。
- `energy_def_high/mid/low` 是 `NOT NULL` 且沒有預設值，spec 沒寫預設文字，草擬如下（Q1）：
  - 高：「需要整段專注，做完會明顯疲累」
  - 中：「正常節奏可以完成」
  - 低：「零碎時間就能處理」
- `PUT /settings`：只接受 FR-SET-02 的欄位，未知欄位回 `VALIDATION_ERROR`。DDL 沒擋、但 FR 有列選項的欄位，在 API 層驗證：
  - `confirm_time` ∈ `12:00`／`18:00`／`21:00`
  - `goal_types_enabled` ⊆ `growth`／`time`／`expectation`，不可重複
  - `energy_def_*` 非空、≤ 200 字
- 設定不寫 `events`（`events.kind` 沒有設定類），也不需要 `expected_version`：單一使用者、單列，後寫覆蓋前寫。
- `onboarding/complete`：第一次呼叫寫 `onboarded_at`，之後再呼叫回 200、不改時間。`skipped=true` 時另確保量表 v0 存在（FR-SET-01）。
- 改 `retention_days` 時，既有來源的期限怎麼算 → Q2。

## 3. 量表（8.2～8.4）

### 3.1 v0 與目前版本

- v0：`version=0`、`source='default'`，`levels` 用 FR-SET-04 的五個名稱：「未達成」「部分達成」「符合預設」「優於預設」「遠超預設」。和設定一樣以 `ensure_defaults` 補上（Q1）。
- 目前版本 = `version` 最大的那筆。
- **不可變**：repo 只提供 INSERT 與 SELECT，沒有 UPDATE、DELETE 路徑；測試斷言沒有任何端點能改既有版本。要不要在資料庫層加觸發器 → Q3。

### 3.2 AI-06 介面（我是 `AIClient` 契約擁有者，只定義節點輸入輸出，不改 `call` 簽名）

輸入 `payload`：`{ "q1": "…", "q2": "…", "q3": "…", "current": [目前版本 5 句] }`
- `current` 讓 AI 以現行量表為底改寫。三題回答各 ≤ 200 字，非空。不送任務、來源或任何對話原文。

輸出：`{ "levels": ["…", "…", "…", "…", "…"] }`
- 驗證：剛好 5 個非空字串、各 ≤ 200 字；否則視為 `invalid_output`。
- 重試比照 AI-01：逾時、格式不符最多 3 次；`AIUnavailable` 不重試。
- 最終失敗一律回 503 `AI_UNAVAILABLE`（spec 5.4、6.6），不回 200＋`ai_status`。這是 spec 4.3「AI 端點回 200」的明定例外。
- 每次呼叫寫一筆 `ai_runs(node_id='AI-06')`，`raw_output` 存輸出，`error` 只放例外類別名稱。
- 成功回 `{ "ai_status": "ok", "draft": [5 句] }`。草稿不入庫，只存在前端，符合「確認前不入統計」。

### 3.3 確認為新版本（8.4）

- `POST /rubrics` 輸入 `{ "levels": [5 句], "interview": { "q1", "q2", "q3", "draft"? } }`。
- `levels` 剛好 5 句、各非空且 ≤ 200 字，否則 `VALIDATION_ERROR`（spec 5.4）。
- `version = 目前最大值 + 1`，`source='interview'`，`interview` 原樣存（含 q3，FR-RUB-04 只記錄不實作）。單一使用者，`version` 的 UNIQUE 約束足以擋下極少見的同時送出。
- `interview.draft` 有帶時，另寫一筆 `ai_feedback(node_id='AI-06', target_type='rubric')`：`levels` 與草稿完全相同記 `accepted`，否則 `edited` → Q4。
- 回 `{ "id", "version" }`。

## 4. 每日清除（8.5，AC-52）

- 清除內容：`UPDATE sources SET excerpt = NULL, purged_at = now WHERE expires_at <= now AND excerpt IS NOT NULL`；這一輪有清到原文時，`idempotency_keys` 全部刪除（快取的回應本文可能含剛清掉的原句，資安審查發現）；沒清到時只刪超過 24 小時的列（DA-23）。改保存期限時走同一個函式。`events`、`candidates` 不動。
- 這個操作是冪等的：重複執行只會清到新到期的列。
- 排程方式 → Q5。實作放在 `app/scheduler.py`，與 `worker.py` 同一個行程、獨立的背景執行緒；測試直接呼叫 `purge_expired(db)`，不啟動執行緒（和 Phase 7 背景工作同一套作法）。
- 日誌只記清除筆數（資安規則 3）。

## 5. 刪除所有來源原文（8.6，AC-53）

- 沒帶 `confirm: true`（缺漏、`false`、非布林）→ 422 `VALIDATION_ERROR`，資料庫不變。
- 帶了 → 同一個交易內：
  1. `sources`：所有 `excerpt IS NOT NULL` 的列設 `excerpt = NULL`、`purged_at = now`。
  2. `idempotency_keys`：全部刪除（DA-23：快取的回應本文可能含原句）。
- 不動：`events`、`candidates`、`tasks`、`ai_runs`、`jobs`（spec 6.7、CLAUDE.md 資安 5）。我盤點過其他欄位：`jobs.payload` 只存 source id，AI-01 的 `raw_output` 只有 ref／kind／task_id／日期，都沒有原文，不必清。
- 回 `{ "purged": 清除的來源數 }`。歷程與候選畫面在 `purged_at` 有值時顯示「已刪除」，Phase 5、7 已經這樣做。

## 6. 匯出（8.7，AC-54）

- 範圍：0001 遷移建立的全部 17 張表，`alembic_version` 除外（那是遷移工具的帳，不是使用者資料）。包含 `idempotency_keys`、`confirmations` 這類暫存表，因為 AC-54 要求「含所有表」。
- 一致性：整份匯出在**同一個 REPEATABLE READ 交易**裡讀，所有表看到同一個時間點，筆數才會和資料庫一致。
- 格式：`{ "exported_at", "schema_version", "counts": { 表名: 筆數 }, "tables": { 表名: [列…] } }`。時間轉 ISO 8601，`JSONB` 原樣巢狀。已清除的 `excerpt` 自然是 `null`。
- 回應直接是 JSON 本文，標頭帶 `Content-Disposition: attachment; filename="export-YYYYMMDD-HHMMSS.json"`。**伺服器不落地存檔**：匯出檔含原文，多存一份就多一個要清除的位置。
- 匯出不寫事件，日誌只記各表筆數。
- **不經冪等快取**：`IdempotencyMiddleware` 會把帶 `Idempotency-Key` 的 JSON 回應整份存進 `idempotency_keys`，匯出檔含全部原文，存進去就多一份副本。所以 `/export` 列入中介層的跳過清單（實作時發現，改 Dev-A 的 `middleware.py` 一行，記為 N-05）。
- 表清單從 `information_schema` 讀 `public` 下的資料表（排除 `alembic_version`），不寫死；之後新增的遷移表會自動納入。

## 7. 裁定（2026-11-15，全部採建議欄）

| # | 問題 | 選項 | 建議 | 後果 |
| --- | --- | --- | --- | --- |
| Q1 | 設定預設列與量表 v0 由誰建立 | A. 程式啟動與 `GET` 時補（`ON CONFLICT DO NOTHING`）；B. 新增 0002 資料遷移 | **A** | B 會動到 Dev-A 擁有的遷移鏈，且 QC 種子若指定 `rubrics.id=1`、`version=0` 會撞號；A 不碰契約。同時請確認第 2 節的三句精力定義預設文字 |
| Q2 | 改保存期限後，既有來源怎麼算 | A. 只影響之後收的來源（沿用已存的 `expires_at`）；B. 改設定時重算未清除來源的 `expires_at = received_at + 新天數` | **B** | A 最簡單且符合 spec 6.7 字面，但使用者從 180 天改成 30 天時，舊原文還會留到 180 天，和他的預期相反；B 多一個同交易內的 UPDATE |
| Q3 | 量表不可變要不要加資料庫觸發器 | A. 只靠程式（沒有更新路徑＋測試）；B. 請 Dev-A 加 0002 遷移，比照 `events` 擋 UPDATE／DELETE | **A** | B 防護較強但要改凍結契約、走變更流程；目前只有 Dev-B 寫這張表，A 已足夠。AC 沒有要求資料庫層 |
| Q4 | 確認量表時要不要記 AI 採用情形 | A. 前端在 `interview` 帶 `draft`，後端寫 `ai_feedback`；B. 不記 | **A** | `ai_feedback.target_type` 已預留 `rubric`，A 讓 AI-06 的接受率可以算；只是選填欄位，前端（Dev-C／我自己做 12.x）要知道 |
| Q5 | 每日清除怎麼排程 | A. 每小時跑一次冪等清除（啟動時先跑一次）；B. 嚴格在每天 03:00 跑 | **A** | spec 寫 03:00 是為了避開使用時段，但本機服務 03:00 常常沒開機，B 會整天漏跑；A 讓到期原文最晚 1 小時內清掉，對隱私更嚴格。需要把 spec 6.7 改成「每小時」 |
| Q6 | 匯出是否包含 `ai_runs.raw_output` 等中間產物 | A. 全部照匯；B. 排除暫存表與中間產物 | **A** | AC-54 寫「含所有表、筆數一致」，B 會讓 QC 的驗收不過；這些欄位已確認不含對話原文 |

## 8. 檔案配置（照既有分層）

| 層 | 檔案 | 內容 |
| --- | --- | --- |
| API | `app/api/routes_settings.py` | 設定、onboarding、量表 4 個端點 |
| API | `app/api/routes_governance.py` | `/sources/purge`、`/export` |
| 商業邏輯 | `app/domain/settings.py` | 預設值、欄位驗證、保存期限重算（Q2） |
| 商業邏輯 | `app/domain/rubrics.py` | v0、AI-06 呼叫與驗證、新版本 |
| 商業邏輯 | `app/domain/governance.py` | 到期清除、全部清除、匯出 |
| 資料存取 | `app/db/repo/settings_repo.py`、`rubrics_repo.py` | 新檔；`misc_repo.active_rubric_id` 是 Dev-A 在用的，留在原處不搬，避免合併衝突 |
| 資料存取 | `app/db/repo/sources_repo.py` | 加清除函式 |
| 排程 | `app/scheduler.py` | 清除執行緒；`main.py` 啟動時和 worker 一起啟動 |

`sources_repo.retention_days` 目前在沒有設定列時回 30；Q1 定案後改讀 `settings_repo`，單一事實來源。

## 9. 驗收對照

| AC／FR | 測試 |
| --- | --- |
| AC-52 | 種子 30 天期限、已過期與未過期各一筆來源＋其事件與候選 → `purge_expired` → 只有過期的 `excerpt` 為 NULL、`purged_at` 有值；事件、候選筆數不變 |
| AC-53 | 無 `confirm`、`confirm=false`、`confirm="true"` 都回 422 且資料不變；`confirm=true` → 全部 `excerpt` 為 NULL、`idempotency_keys` 清空、事件不變 |
| AC-54 | 種子各表資料 → 匯出 → 合法 JSON、17 張表都在、每張表筆數等於 `SELECT count(*)` |
| FR-SET-01～03 | 預設值、部分更新、非法選項 422、onboarding 重複呼叫不改時間 |
| FR-SET-04、FR-RUB-01 | 沒有量表時 `?active=true` 回 v0；確認後版本遞增、舊版內容不變 |
| FR-RUB-02、03 | FakeAIClient：正常回草稿；5 句以外、空字串觸發重試；不可用回 503 且不建新版 |
| 資安 | AI-06 payload 只有三題回答與目前量表；日誌只有筆數與例外類別 |
