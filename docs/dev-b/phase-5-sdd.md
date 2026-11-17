# Phase 5 SDD：歷程查詢與甘特資料（Dev-B）

依據：spec 3.3（FR-PRJ-04、05）、3.10（FR-HIS-03～07）、5.5、5.8；todo Phase 5（5.1～5.6）；AC-27、28、34、56。
性質：**純讀取**，不寫任何資料，不呼叫 `write_event`、`adjust_due`。

## 1. 端點

| Method | Path | 任務 | 說明 |
| --- | --- | --- | --- |
| GET | `/events` | 5.1–5.3 | 歷程查詢，篩選加分頁 |
| GET | `/projects/{id}/history` | 5.1 | 等同 `/events?project_id={id}`，其他參數照樣可用 |
| GET | `/projects/{id}/gantt` | 5.4–5.5 | 甘特資料與專案現況摘要 |

### 1.1 `GET /events` 參數

| 參數 | 規則 |
| --- | --- |
| `project_id` | 整數或 `none`；`none` 表示只查 `project_id IS NULL`（單點任務，AC-05、AC-27） |
| `kind` | 8 種事件類型之一，其他值回 `VALIDATION_ERROR` |
| `task_id`、`batch_id` | 整數 |
| `from`、`to` | 日期，含頭含尾，以台北時間的日期比對 `ts`（與 Dev-A 的 `mine_due_events_with_effective_mark` 相同） |
| `limit` | 預設 100，最大 500，超過回 `VALIDATION_ERROR` |
| `offset` | 預設 0 |

排序：`ts DESC, id DESC`（同一交易內的事件 `ts` 相同，用 `id` 當平手項，分頁才不會重複或漏掉）。
`total` 是符合條件的總筆數，不受 `limit`／`offset` 影響。

### 1.2 每筆輸出

照 spec 5.8 的範例，另外補三點：

- `project_name`：LEFT JOIN `projects`；單點任務為 `null`。
- `effective_mark`：只有 `due` 事件才算（最新一筆 `annotation` 的 mark，沒有就取原事件 mark）；其他類型一律 `null`。
- `source`：一律回物件 `{label, quote, purged}`，前端不必判斷有沒有這個欄位。
  - `quote`：有 `source_id` 且 `excerpt` 未清除時是原句，其餘情況為 `null`。
  - `purged`：`sources.purged_at` 不為空時是 `true`（AC-28）。
  - `label`：依 `origin` 產生，見第 4 節 Q2。

## 2. 甘特資料 `GET /projects/{id}/gantt`

- `rows`：專案內所有任務，**包含已完成的**，依 `start_date, id` 排序。每列欄位照 spec 5.5 範例：`task_id, title, owner, status, start, orig_due, latest_due, delta_days, done_date, blocked, version`。
  - 三種區間（進行、基準框、延後）由前端用 `start`／`orig_due`／`latest_due`／`done_date` 畫，後端不另外算區間座標。這樣只有一個事實來源，甘特圖怎麼畫屬於 Dev-C 的 12.1。
  - `delta_days = latest_due − orig_due`；是負數時，前端標「提前 n 天」。
- `range`：`from = min(start)`；`to = max(orig_due, latest_due, done_date)`；專案沒有任務時為 `null`。
- `today`：取自應用程式時鐘（`get_clock()`），不用資料庫的 `CURRENT_DATE`。
- `summary`：
  - `done`、`total`：直接算任務數。
  - `delayed`：重用 Dev-A 的 `TaskRepo.delayed_count`（spec 4.4）。
  - `open_candidates`：見第 4 節 Q1。

AC-34：甘特圖和摘要只讀 `tasks`，`open` 候選不會改動 `tasks`，所以自然不受影響；另寫測試鎖住這個行為。

## 3. 檔案配置（照 Dev-A 的分層）

| 層 | 檔案 | 內容 |
| --- | --- | --- |
| 資料存取 | `db/repo/history_repo.py`（新） | `search_events(filters, limit, offset) -> (rows, total)`、`gantt_tasks(project_id)`、`open_candidate_count(project_id)` |
| 規則 | `domain/history.py`（新） | 篩選參數檢查、`source` 物件組裝與 label 對照、`range` 計算 |
| 介面 | `api/routes_history.py`（新） | 三個端點；`main.py` 加一行 `include_router` |
| 測試 | `tests/unit/test_phase5_history.py`（新） | 以 SQL 種子建資料，依 AC 編號命名 |

不改 Dev-A 的檔案。唯一例外是在 `main.py` 註冊新路由，只加一行。

## 4. 歧義裁定（2026-11-15 產品負責人：Q1–Q4 依建議定案）

| # | 歧義 | 我的建議 | 影響 |
| --- | --- | --- | --- |
| Q1 | `candidates` 沒有 `project_id` 欄位，專案的「待確認候選數」不知道怎麼算 | 計算「`state=open` 且對應任務屬於這個專案」的候選數。`unmatched`（沒有對應任務）不算進專案，留在收件匣顯示 | FR-PRJ-04、AC-34；若要算 `unmatched`，就需要 Dev-A 新增遷移，在 `sources` 加 `project_id` |
| Q2 | spec 只給了 `label` 的一個例子「候選 #12」 | `candidate`→「候選 #id」、`bulk`→「整批順延 #batch_id」、`import`→「匯入」、`baseline_correction`→「基準更正」、`manual`→「手動」、`system`→「系統」 | FR-HIS-04；只影響顯示文字 |
| Q3 | `limit` 超過 500 時，回錯誤還是自動降到 500 | 回 `VALIDATION_ERROR`，和其他參數錯誤一致 | spec 5.8 |
| Q4 | AC-56 效能（300 ms）可能需要 C-12 建議的 `(project_id, ts DESC, id DESC)` 索引 | 先用現有索引量測；不達標再提遷移需求給 Dev-A（遷移只有 Dev-A 能動） | AC-56、todo 5.6 |

## 5. 驗收對照

| AC | 測試 |
| --- | --- |
| AC-27 | 多專案、多種事件，以 `project_id`／`kind`／`task_id` 組合篩選；`total` 正確；`project_id=none` 只回單點任務事件 |
| AC-28 | 種子一筆 `excerpt=NULL`、`purged_at` 有值的來源 → `purged=true`、`quote=null`，事件仍在 |
| AC-34 | 種子 `open` 候選 → 甘特圖與 `summary.delayed` 不變，`open_candidates` 計數正確 |
| AC-56 | 種子 1,000 個任務、10,000 筆事件，`GET /events` 帶篩選 < 300 ms（本機量測，標〔假設〕）。2026-11-15 實測 10–20 ms（Windows＋Docker PostgreSQL 17），現有索引足夠，Q4 不需新增遷移 |
| 分頁 | 同一 `ts` 的多筆事件跨頁不重複、不遺漏 |
