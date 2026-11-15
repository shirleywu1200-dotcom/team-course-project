# Phase 6 SDD：專案匯入（Dev-B）

依據：spec 3.4（FR-IMP-01～07）、5.6、6.6（AI-07 退路）；todo Phase 6（6.1～6.7）；AC-30～33、55。
寫入路徑：新專案用 Dev-A 的 `create_project`；任務用 `TaskRepo.insert`；事件只經 `write_event`。

## 1. 端點（spec 5.6）

| Method | Path | 任務 | 說明 |
| --- | --- | --- | --- |
| POST | `/projects/import/preview` | 6.1–6.5、6.7 | 解析、對應表頭、診斷；**不寫任何業務資料**（只寫 AI-07 的 `ai_runs`） |
| POST | `/projects/import/commit` | 6.6 | 伺服器重新驗證後，在單一交易內建立任務與一筆 `baseline` 事件 |

## 2. preview 流程

```
大小檢查 → 切表格 → 表頭對應（規則 → 不足才 AI-07 → 仍不足回 mapped_by=null）→ 每列解析日期與診斷 → 回傳
```

### 2.1 切表格（6.1）

- 用 Python 標準函式庫的 `csv` 解析，所以欄位內含逗號時可以用引號包起來。
- 分隔符看表頭那一行：有 Tab 就用 Tab，否則用逗號（FR-IMP-01）。
- 去掉前後空白；整列都空白就跳過，不算列。
- 上限：超過 50,000 字元或超過 500 列（不含表頭）→ 413 `PAYLOAD_TOO_LARGE`。

### 2.2 表頭對應（6.2、6.5）

**規則**：表頭去掉空白、轉小寫後，看是否含下列關鍵字。

| 欄位 | 關鍵字 |
| --- | --- |
| `title` | 任務、名稱、工作、項目、title、task、name |
| `owner` | 負責、owner、assignee、pic |
| `start` | 開始、起始、start |
| `end` | 結束、期限、截止、到期、完成、due、end、deadline |

- 同一欄只對應一個欄位，依 `title → owner → start → end` 的順序認領。
- `title` 和 `end` 都有對應到 → `mapped_by="rule"`，**不呼叫 AI**。
- 缺 `title` 或 `end` → 呼叫 AI-07（6.5）。AI 結果合法 → `mapped_by="ai"`；AI 不可用或輸出不合法 → `mapped_by=null`，`column_map` 只保留規則已對應的欄位，前端讓使用者手動指定（AC-33）。
- 請求帶了 `column_map` → 直接使用，不跑規則也不呼叫 AI，`mapped_by="manual"`（見 Q1）。

**AI-07 介面**（我是 `AIClient` 契約擁有者，定義節點輸入輸出）：

```json
輸入 { "headers": ["工項", "PIC", "起", "交期"], "samples": [["需求確認", "我", "11/16", "11/18"]] }
輸出 { "title": 0, "owner": 1, "start": 2, "end": 3 }
```

- `samples` 最多 2 列，用來輔助判斷，見 Q4。
- 輸出驗證：`title`、`end` 必須是不重複的整數欄位索引，`owner`、`start` 可以是 null；不合格式就視為 `invalid_output`。
- 只呼叫 1 次、不重試：preview 是互動操作，退路是讓使用者手動指定，比讓使用者等重試好。
- 每次呼叫都寫一筆 `ai_runs`。

### 2.3 日期（6.3）

- 接受 `YYYY-MM-DD`、`YYYY/M/D`、`YYYY年M月D日`、`M/D`、`M月D日`。
- `M/D` 推年規則（見 Q2）：取今年；如果比今天早 180 天以上，算明年。與 Phase 7 共用同一個函式（`r2.to_date` 搬到 `domain/dates.py`）。
- 無法解析 → 視為缺日期（FR-IMP-03）。

### 2.4 診斷（6.4，AC-30）

| 等級 | code | 條件 | 處理 |
| --- | --- | --- | --- |
| error | `TITLE_MISSING` | 缺任務名稱 | blocking |
| error | `END_MISSING` | 缺結束日，或日期無法解析 | blocking |
| error | `END_BEFORE_START` | 結束早於開始 | blocking |
| error | `DATE_OUT_OF_RANGE` | 結束日超出允許範圍（今天前 365 天至後 730 天，與日期調整相同） | blocking（見 Q5） |
| warn | `OWNER_MISSING` | 缺負責人 | 預設「我」 |
| warn | `START_MISSING` | 缺開始日，或日期無法解析 | 以結束前 3 天代入 |
| warn | `DUPLICATE_TITLE` | 名稱與前面某列相同（只比這張表，不比專案既有任務） | 可匯入 |

- 回傳的 `rows` 已經套用預設值：`owner` 為「我」，`start` 為代入的日期。前端直接拿來顯示，commit 時原樣送回。
- `summary`：`importable` 是沒有 blocking 的列數，`blocking` 是有 blocking 的列數。

## 3. commit（6.6，AC-31、32）

輸入照 spec 5.6，每列有 `index, title, owner, start, end, skip`。

1. **重新驗證**：每一列都用 2.3、2.4 的同一套規則重跑一次，不相信前端送來的 `blocking`。有 blocking 而且沒標 `skip` 的列 → 422 `VALIDATION_ERROR`，`details.rows` 列出這些列號，什麼都不寫（AC-31）。
2. 可匯入列為 0 → 422 `EMPTY_SELECTION`（FR-IMP-05）。
3. 在單一交易內：
   - `target="new"` 時，用 `create_project(name=new_name)` 建立專案；`target=<id>` 時確認專案存在且未封存。
   - 每列用 `TaskRepo.insert` 建立任務：`orig_due = latest_due = end`、`start_date = start`、`star_source = 'import_default'`、`scope` 取專案的範圍、`rubric_id` 取目前量表。
   - 寫**一筆**事件：`kind='baseline'`、`field='import'`、`origin='import'`、`project_id`、`task_id=NULL`、`to_value=建立數`、`extra={"created": n, "skipped": m, "task_ids": […]}`。
   - 任一步失敗 → 整筆回滾，一列都不留（AC-32）。
4. 輸出：`{ "project_id", "created", "skipped", "event_id" }`。`skipped` 是標了 `skip` 的列數。

`baseline` 事件寫入後，Dev-A 的專案詳情 `baseline_saved_at` 會自動有值（它讀最新一筆 `baseline` 事件），不必另外處理。

## 4. 檔案配置

| 層 | 檔案 | 內容 |
| --- | --- | --- |
| 規則 | `domain/dates.py`（新） | `to_date`（從 Phase 7 的 `r2.py` 搬過來，兩邊共用） |
| 規則 | `domain/imports/table.py` | 切表格、表頭規則對應（純函式） |
| 規則 | `domain/imports/diagnose.py` | 單列解析與診斷（純函式，preview 與 commit 共用） |
| 規則 | `domain/imports/service.py` | preview（含 AI-07）、commit（交易） |
| 介面 | `api/routes_import.py` | 兩個端點；要掛在 `/projects/{id}` 之前，避免 `import` 被當成專案 id |
| 測試 | `tests/unit/test_phase6_*.py` | 純函式測試＋端點測試；AC-55 計時 |

`ai_runs` 沿用 Phase 7 的 `ai_runs_repo`；不需要新的資料表或遷移。

## 5. 歧義裁定（2026-11-15 產品負責人：Q1–Q6 依建議定案）

| # | 歧義 | 我的建議 | 影響 |
| --- | --- | --- | --- |
| Q1 | AC-33 說「使用者可手動指定」，但 preview 的輸入沒有欄位可以放手動對應 | preview 輸入加選填的 `column_map`（`{title, owner, start, end}` 欄位索引）；有帶時 `mapped_by="manual"` | 契約新增：`mapped_by` 多一個值 `manual`、輸入多一個欄位；記在 `requests-to-dev-a.md` 的通知區，並通知 Dev-C、QC-2 |
| Q2 | `M/D` 要「依專案期間推年」，但新專案還沒有期間 | 一律以今天為基準：比今天早 180 天以上就算明年。跨年的專案（12/20 → 1/10）會被正確推成同一個期間 | 與 Phase 7 的日期規則一致，只有一套規則要記 |
| Q3 | 每個匯入的任務要不要各寫一筆「建立任務」事件 | 不寫，照 spec 只寫**一筆** `baseline` 事件，`extra.task_ids` 列出這次建立的任務 | 500 列匯入只寫 1 筆事件；各任務的歷程從「匯入基準」這筆開始。若要逐筆寫，會變成 500 筆事件 |
| Q4 | AI-07 要送哪些資料 | 送表頭＋最多 2 列樣本。目標專案是私人範圍時**不呼叫 AI**，直接回 `mapped_by=null`（資安規則 2） | 樣本裡可能有人名；只看表頭，AI 的對應準確度會差很多 |
| Q5 | 結束日超出日期允許範圍（例如兩年前的舊專案）要不要擋 | 列為 error（blocking），與手動調整日期的範圍一致 | 匯入很舊的專案時，這幾列要略過；若要允許，日期範圍規則就不一致 |
| Q6 | AI-07 的 `ai_feedback`（FR-AI-04：使用者有沒有改 AI 的對應） | 本 Phase 不記。commit 不帶對應資訊，preview 又是無狀態的，判斷不出使用者有沒有改 | 若要記，commit 要多帶 `column_map` 與 `mapped_by`；屬於契約新增，等前端 12.7 實作時再決定 |

## 6. 驗收對照

| AC | 測試 |
| --- | --- |
| AC-30 | 7 列：缺結束、結束早於開始各 1 列 → blocking；重複名稱、缺負責人 → warn；`importable=5`、`blocking=2` |
| AC-31 | commit 帶未略過的錯誤列 → 422，`details.rows` 列號正確；任務與事件數不變 |
| AC-32 | 全部合法 → 任務欄位正確、1 筆 `baseline` 事件；模擬中途失敗 → 一列都不留 |
| AC-33 | 非標準表頭：規則不足才呼叫 AI → `mapped_by="ai"`；AI 不可用 → `mapped_by=null`；標準表頭 → 沒有呼叫 AI |
| AC-55 | 500 列 preview < 2 秒（不含 AI-07） |
| 其他 | 413 上限、Tab 與引號、`M/D` 跨年、新專案與既有專案、封存專案、私人專案不呼叫 AI、手動 `column_map` |
