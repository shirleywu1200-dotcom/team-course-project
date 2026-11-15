# Dev-B 對 Dev-A 的調整請求與通知

Dev-B 開發時發現、需要 Dev-A 處理或知道的事項，**統一記在這裡**（2026-11-15 產品負責人指示）。
「請求」需要 Dev-A 動手；「通知」是 Dev-B 已在自己分支處理、合併時請 Dev-A 知悉的改動。

| 狀態 | 意義 |
| --- | --- |
| 待處理 | 已記錄，尚未交給 Dev-A |
| 已提出 | 已告知 Dev-A，等回覆 |
| 已完成 | Dev-A 已處理，或確認不需處理 |

## 請求

### R-01 `create_task` 加 `origin`、`origin_ref`、`source_id` 選填參數　〔待處理〕

- **來源**：Phase 7 SDD Q5；FR-INB-14、FR-HIS-04。
- **內容**：比照 `set_blocked`、`complete_task`，在 `app/domain/tasks.py` 的 `create_task` 加三個選填關鍵字參數，預設 `origin="manual"`，並傳給 `write_event`。舊呼叫不受影響。
- **原因**：從 `unmatched` 候選建立任務時，建立事件要記「依據候選 #id 與原句」；現在只能記成 `manual`，歷程看不出任務是從哪則訊息來的。
- **Dev-B 暫行做法**：先以 `origin="manual"` 呼叫；Dev-A 加上參數後，Dev-B 改一行即可。

### R-02 部署文件改成跨平台指令　〔待處理〕

- **來源**：2026-11-15 Windows 環境建置。
- **內容**：`docs/deploy.md`、`docs/dev-a-progress.md`、`docs/decisions.md`、`app/export_openapi.py` 裡的 `.venv/bin/<指令>` 改成 `uv run <指令>`（例如 `uv run alembic upgrade head`、`uv run pytest`）。
- **原因**：`.venv/bin/` 只有 Mac／Linux 有，Windows 是 `.venv\Scripts\`。`uv` 本來就在技術棧裡，`uv run` 兩種系統都能用，不必分兩套說明。

### R-03 範例 port `54329` 換一個值　〔待處理〕

- **來源**：2026-11-15 Windows 環境建置。
- **內容**：`env/example.env`、`docs/deploy.md` 的 `54329`。
- **原因**：Windows 會保留一段動態 port 範圍，各台電腦不同；本機保留了 54315–54414，`54329` 綁不上，Docker 直接啟動失敗。建議改用 `5433` 這類常見又不太會撞到保留範圍的值，或在文件中註明「綁不上就換」。

## 通知（Dev-B 已在 `dev-b/phase-5-8` 處理）

### N-01 `backend/alembic.ini` 註解改為純 ASCII　〔已完成〕

- Alembic 讀這個檔時用系統語系編碼（Windows 繁中為 cp950），不受 `PYTHONUTF8` 影響；原本的中文註解會讓 `alembic upgrade` 直接失敗。只改了註解，設定值不變。

### N-02 `scripts/hooks/pre-commit` 支援 Windows 的 ruff 路徑　〔已完成〕

- 找不到 `.venv/bin/ruff` 時改用 `.venv/Scripts/ruff.exe`。Mac 行為不變。

### N-03 `POST /ingest` 回應新增 `result.unparsed_lines`　〔已完成，需通知 Dev-C、QC-2〕

- Phase 7 SDD 2.1：無法辨識的行號清單，供使用者修正後重貼。是新增欄位，不改既有欄位。

### N-04 匯入 preview 新增手動對應　〔已完成，需通知 Dev-C、QC-2〕

- Phase 6 SDD Q1：`POST /projects/import/preview` 輸入多一個選填欄位 `column_map`（`{title, owner, start, end}` 欄位索引）；帶了時回 `mapped_by="manual"`。`mapped_by` 原本只有 `rule`、`ai`、`null`，現在多一個值。
