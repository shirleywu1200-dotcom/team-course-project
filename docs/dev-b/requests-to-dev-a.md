# Dev-B 對 Dev-A 的調整請求與通知

Dev-B 開發時發現、需要 Dev-A 處理或知道的事項，**統一記在這裡**（2026-11-15 產品負責人指示）。
「請求」需要 Dev-A 動手；「通知」是 Dev-B 已在自己分支處理、合併時請 Dev-A 知悉的改動。

| 狀態 | 意義 |
| --- | --- |
| 待處理 | 已記錄，尚未交給 Dev-A |
| 已提出 | 已開 GitHub issue 指派給對方，issue 關閉即完成 |
| 已完成 | Dev-A 已處理，或確認不需處理 |

## 請求

### R-01 `create_task` 加 `origin`、`origin_ref`、`source_id` 選填參數　〔Dev-A 已完成（d081477）；收件匣已改用〕

- **來源**：Phase 7 SDD Q5；FR-INB-14、FR-HIS-04。
- **內容**：比照 `set_blocked`、`complete_task`，在 `app/domain/tasks.py` 的 `create_task` 加三個選填關鍵字參數，預設 `origin="manual"`，並傳給 `write_event`。舊呼叫不受影響。
- **原因**：從 `unmatched` 候選建立任務時，建立事件要記「依據候選 #id 與原句」；現在只能記成 `manual`，歷程看不出任務是從哪則訊息來的。
- **Dev-B 暫行做法**：先以 `origin="manual"` 呼叫；Dev-A 加上參數後，Dev-B 改一行即可。

### R-02 部署文件改成跨平台指令　〔已提出：#3〕

- **來源**：2026-11-15 Windows 環境建置。
- **內容**：`docs/deploy.md`、`docs/dev-a-progress.md`、`docs/decisions.md`、`app/export_openapi.py` 裡的 `.venv/bin/<指令>` 改成 `uv run <指令>`（例如 `uv run alembic upgrade head`、`uv run pytest`）。
- **原因**：`.venv/bin/` 只有 Mac／Linux 有，Windows 是 `.venv\Scripts\`。`uv` 本來就在技術棧裡，`uv run` 兩種系統都能用，不必分兩套說明。

### R-03 範例 port `54329` 換一個值　〔已提出：#4〕

- **來源**：2026-11-15 Windows 環境建置。
- **內容**：`env/example.env`、`docs/deploy.md` 的 `54329`。
- **原因**：Windows 會保留一段動態 port 範圍，各台電腦不同；本機保留了 54315–54414，`54329` 綁不上，Docker 直接啟動失敗。建議改用 `5433` 這類常見又不太會撞到保留範圍的值，或在文件中註明「綁不上就換」。

## 通知（Dev-B 已在 `dev-b/phase-5-8` 處理）

2026-11-15 已發 issue：Dev-A 的部分（N-01、N-02、N-05、N-06）為 #5；Dev-C、QC-2 的部分（N-03、N-04、N-06、N-07）為 #6。

### N-01 `backend/alembic.ini` 註解改為純 ASCII　〔已完成〕

- Alembic 讀這個檔時用系統語系編碼（Windows 繁中為 cp950），不受 `PYTHONUTF8` 影響；原本的中文註解會讓 `alembic upgrade` 直接失敗。只改了註解，設定值不變。

### N-02 `scripts/hooks/pre-commit` 支援 Windows 的 ruff 路徑　〔已完成〕

- 找不到 `.venv/bin/ruff` 時改用 `.venv/Scripts/ruff.exe`。Mac 行為不變。

### N-03 `POST /ingest` 回應新增 `result.unparsed_lines`　〔已完成，需通知 Dev-C、QC-2〕

- Phase 7 SDD 2.1：無法辨識的行號清單，供使用者修正後重貼。是新增欄位，不改既有欄位。

### N-04 匯入 preview 新增手動對應　〔已完成，需通知 Dev-C、QC-2〕

- Phase 6 SDD Q1：`POST /projects/import/preview` 輸入多一個選填欄位 `column_map`（`{title, owner, start, end}` 欄位索引）；帶了時回 `mapped_by="manual"`。`mapped_by` 原本只有 `rule`、`ai`、`null`，現在多一個值。

### N-05 `IdempotencyMiddleware` 跳過 `/export`　〔已完成〕

- Phase 8 SDD 第 6 節：匯出回應含全部原文，帶 `Idempotency-Key` 時會整份存進 `idempotency_keys`，多一份清除不到的副本。`middleware.py` 新增 `NO_CACHE_PATHS`，`/export` 不經快取；其他端點行為不變。

### N-06 spec 6.7 清除排程改為每小時、改保存期限會重算期限　〔已完成，需通知 QC-2〕

- Phase 8 SDD Q2、Q5（2026-11-15 產品負責人裁定）。spec FR-GOV-01、6.7、AC-52 的「每日排程」改為「清除排程」，QC 的 AC-52 測試措辭請對應。
- `sources_repo.retention_days` 已移除，收件改從 `app/domain/settings.get_settings` 取保存期限（沒有設定列時自動補預設列）。

### N-07 收件匣（12.8）加進 Dev-A 的前端暫代檔　〔已完成，需通知 Dev-C〕

- 12.8 SDD D-1：沿用 Dev-A 的暫代骨架。Dev-C 做 0.8、Phase 11 時，下列 Dev-B 新增的部分要一併吸收：
  - `src/api/types.ts`：`Candidate`、`IngestResult`、`IngestJob`、`DecideResult`、`AppSettings`
  - `src/api/queries.ts`：`keys.candidates`、`keys.settings`、`keys.ingestJob` 與對應讀取函式
  - `src/test/server.tsx`：`makeCandidate`，以及 `GET /settings`、`GET /candidates` 的預設 handler
  - `src/components/standin/ErrorBanner.tsx`：`CANDIDATE_NOT_OPEN`、`PAYLOAD_TOO_LARGE` 訊息
  - `src/styles/base.css`：`.head`、`.tag`、`.quote`、`.done-item`
  - `src/App.tsx`：`/inbox` 路由
- 12.9 完成後，收件匣確認「完成」可改成直接開完成回報表單（目前只提示到今日頁補填，D-2）。

### N-08 匯入精靈（12.7）加進前端暫代檔　〔已完成，已通知 Dev-C：#7〕

- 12.7 SDD 沿用 12.8 的暫代骨架。Dev-C 做 0.8、Phase 11 時，下列 Dev-B 新增的部分要一併吸收：
  - `src/api/types.ts`：`Project`、`ImportIssue`、`ImportRow`、`ColumnIndexes`、`ImportPreview`、`ImportCommitResult`
  - `src/api/queries.ts`：`keys.projects` 與 `fetchProjects`
  - `src/components/standin/ErrorBanner.tsx`：`PAYLOAD_TOO_LARGE` 訊息改為收件匣與匯入共用
  - `src/styles/base.css`：`main.wide`、`.sr-only`、`.import-split`、`.map-grid`、`.table-wrap`、`.nowrap`、`.tag-ok`／`.tag-error`／`.tag-warn`、`tr.row-error`；匯入頁 ≤ 760px 的斷點
  - `src/App.tsx`：`/import` 路由
- 12.7 SDD D-3（AI-07 回饋寫入 `ai_feedback`）的契約新增已提請產品負責人裁定（#8），核可後另記 N-09。

### N-09 匯入 AI-07 對應回饋寫入 `ai_feedback`（12.7 D-3，#8 核可）　〔後端已完成，已通知 Dev-C：#16〕

- `POST /projects/import/preview`：`column_map` 在 `mapped_by="ai"` 時多出 `ai_run_id`，其他情況不出現（`response_model_exclude_unset`）。
- `POST /projects/import/commit`：選填 `ai_run_id` 與最終 `column_map`，兩者一起送；只帶一項、或 `ai_run_id` 不是 `ok` 的 AI-07 紀錄，回 422 `VALIDATION_ERROR`。不帶時行為不變。
- 一次匯入一筆回饋，錨定 baseline 事件；同一 `ai_run_id` 只寫一次。規則寫回 spec FR-AI-04、5.6 與 AC-63（編號暫定）。
- 前端（Dev-B 12.7）送新欄位要改凍結的 `src/api/types.ts`，先在 #11 告知 Dev-C 再改。

### N-10 Dev-B 20 個端點補回應模型（審查 A4）　〔已完成，已通知 Dev-C：#11〕

- rebase 到 `dev-a/phase-0-4` 後，`test_contract_guards` 要求每個 2xx 都有 schema。模型附加在 `backend/app/api/responses.py` 的「Phase 5～8，Dev-B」各節。
- 執行期回應內容不變（加模型前後 93 筆實際回應比對，僅鍵順序不同）；OpenAPI 新增歷程、甘特、匯入、收件候選、設定、量表、清除、匯出的回應 schema。
- Dev-C 可用生成型別取代 `types.ts` 中 Dev-B 手寫的收件匣與匯入型別；QC-2 可依 OpenAPI 寫驗收。

### N-11 啟用精靈與設定頁（12.11）加進前端暫代檔　〔已完成，已通知 Dev-C：#12〕

- 12.11 SDD D-1(b)：全站守門 `OnboardingGate` 包在暫代 `App.tsx` 的 `<Routes>` 外層；`onboarded_at` 為空時，除 `/onboarding` 外都導向精靈。Dev-C 做 Phase 11 正式路由時要把守門搬過去，否則新使用者不會看到精靈。
- Dev-C 做 0.8、Phase 11 時，下列 Dev-B 新增的部分要一併吸收：
  - `src/api/types.ts`：`AppSettings` 改為完整欄位（原本只有 `confirm_cap_min`）；新增 `GoalType`、`SettingsKey`、`InterviewAnswers`、`Rubric`
  - `src/api/queries.ts`：`keys.activeRubric` 與 `fetchActiveRubric`
  - `src/test/server.tsx`：`makeSettings`、`RUBRIC_V0`；`GET /settings` 預設改回已啟用的完整設定（D-1(c)，既有頁面測試不會被導走），新增 `GET /rubrics` 預設 handler
  - `src/styles/base.css`：`.small`、`.steps`、`ol.levels`、`.settings-split`、`.settings-nav`，以及 ≤ 760px 的斷點
  - `src/App.tsx`：`/onboarding`、`/settings` 路由，首頁加「設定」連結
