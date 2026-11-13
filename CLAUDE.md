# 個人大總管 APP

單一使用者的承諾帳：AI 只提議，使用者確認，系統寫入。團隊為 3 位開發（Dev-A／B／C）與 2 位 QC（QC-1／QC-2），產品負責人裁定規格。

## 規格位置

- `docs/spec.md`：FR、資料模型、API、驗收標準（AC）的單一事實來源。
- `docs/todo.md`：待辦與分工；契約凍結清單在 5.7，PR 規則在 5.8，vibe coding 護欄在第 6 節。
- `docs/三開發兩 QC 銜接圖.html`：W1–W5 的時間銜接與 PR 路徑。

接一張票時，先讀 spec 中該票標註的 FR 與 AC，以及 todo 中該 Phase 的「對外契約」。各人的負責範圍寫在自己的 `CLAUDE.local.md`。

## 不可破原則（spec 1.2、FR-AI-06）

1. **確認前不入統計**：`open` 候選與 AI 草稿只存在候選與草稿表，正式紀錄、統計、甘特圖、週報只讀已確認的資料。
2. **原訂日期只由基準更正改動**：改期只寫 `latest_due`；`orig_due` 只在兩段式基準更正的 commit 時覆蓋。
3. **歷程只增**：每個變更新增一筆 `events`，更正也是新增一筆。
4. **評價由使用者自己下**：延期原因、時間管理註記、自評精力、實際達成星數一律保持空白，等使用者選。

## 開發原則

1. 請把介面、商業邏輯和資料存取分開成不同檔案，不要混在一起。
2. 每個檔案和函式都應該只有一個清楚的責任。如果有做超過一件事的內容，請拆開。
3. 每一份資料應該只有一個單一事實來源。不要在不同元件之間重複複製，所有地方都從同一處讀取。
4. 在我使用之前，請用簡單的方式解釋它的結構和原因——我想要理解它，不只是讓它能跑。
5. 請給我能運作的最簡單版本，不要最聰明的版本。而且請符合我專案裡既有的結構與模式。

## 寫入與交易

- 事件只經 `write_event` 寫入。
- 每次寫入在同一個交易內完成「事件＋任務狀態」；任一步失敗就全部回滾（spec 6.8、AC-57）。
- `star_source`、`overdue_days`、`delta_days`、`mine` 由伺服器計算，前端送來的值一律忽略。
- 修改任務的請求帶 `expected_version`，版本不符回 `STALE_VERSION`。

## 契約與角色邊界

- **凍結契約**：DDL、錯誤格式與錯誤碼、`write_event`、`adjust_due`、`AIClient`／`FakeAIClient`、SQL 種子夾具庫。擁有者與變更規則見 todo 5.7。需要變動時先停下，寫出變更內容與影響，交給擁有者與產品負責人。
- **Dev**：實作與單元測試。QC 的驗收測試與夾具庫由 QC 維護，Dev 唯讀使用；需要新種子資料時向 QC 提需求。
- **QC**：只依 spec 與對外契約（DDL、OpenAPI、函式簽名）寫驗收測試，不讀實作。
- **規格歧義**：停下來，列出歧義、可能做法與影響，交產品負責人裁定。程式只寫已裁定的版本，裁定結果先寫回 spec。

## 測試

- 測試資料用 SQL 種子直接 INSERT，不經上游程式碼建立。
- AI 一律用 `FakeAIClient`；真實供應商只在 Phase 13 接入。
- 前端以 MSW 對 OpenAPI 契約測試，不需後端執行。
- FR-AI-06 防回歸測試（todo 3.5、7.9、9.4、12.2）由 QC 持有，維持原樣。
- 每個 Phase 結束時主幹可部署、既有測試全綠。

## 資料庫：PostgreSQL

- 2026-11-13 裁定採用 PostgreSQL；spec 4.2 已改為 PostgreSQL 版 DDL，與 `backend/app/db/migrations/versions/0001_initial.sql` 相同（`docs/decisions.md` DA-01，待產品負責人複核）。
- SQL 種子的布林欄位寫 `true`／`false`；同一份腳本裡同一張表不要混用指定 id 與自動 id（`backend/tests/fixtures/README.md`）。
- Schema 只經 Alembic 遷移變更；只新增遷移，不改既有欄位語意。
- `events` 的 UPDATE、DELETE、TRUNCATE 由資料庫觸發器擋下（AC-11）。
- 業務操作一律經 `Database.run(fn)`：一個操作一個交易，例外即整筆回滾。

## 資安規則

寫或改後端程式前先對照；做不到時停下來說明，不自行繞過。

1. **認證集中**：所有 API 經同一個 Bearer token 相依項驗證，token 來自環境變數；預設只綁 `127.0.0.1`。系統只有單一使用者，沒有角色或成員權限。
2. **對外只經 `AIClient`**：LLM 呼叫只寫在 `AIClient` 的實作裡。送出內容只含必要摘錄與任務清單，私人範圍在送出前排除（FR-RPT-01、FR-GOV-05）。不新增其他對外管道（第三方 API、遙測、錯誤回報服務）。
3. **日誌只記識別資訊**：log、例外訊息、錯誤回應的 `details`、`ai_runs.error`、`jobs.error` 只放 ID、錯誤碼、計數，不放摘錄原文、對話內容或 token。`ai_runs.raw_output` 依 spec 保存，屬於資料，不是日誌。
4. **祕密放 `env/local.env`**：API key、token、資料庫密碼都放這裡（已列入 `.gitignore`）；`env/` 下其他檔案只放外流也無妨的本機開發值。
5. **原文能清除，歷程保留**：資料控制只清 `sources.excerpt`，`events`、`candidates`、`tasks` 保留（FR-GOV-01、03，spec 6.7）。新增存放對話原文的欄位時，在同一張票把它納入清除與匯出範圍，並補測試。
6. **SQL 只用 SQLAlchemy 參數化查詢**，不拼字串。
7. **資安審查**：碰到認證、`AIClient`、資料控制（清除、匯出）、基準更正的票，在 `/code-review` 之後再跑 `/security-review`。repo 還沒有遠端時，`/security-review` 比對不到 `origin/HEAD` 而無法啟動，改交子代理依同樣範圍與判定準則審查。
8. **入庫前掃描**：每次 commit 都經過 `scripts/hooks/pre-commit`（gitleaks 與 ruff 資安規則；`git init` 後執行一次 `scripts/install-hooks.sh`）。誤判時修正程式，或在該行加 `# noqa: <規則>` 並寫明原因，不用 `--no-verify`。

## 前端規範

完整內容將寫在 `docs/ui-guidelines.md`（待建，Phase 11）；建好後寫畫面前先讀。

1. 技術棧依 spec 8.1：React 18、TypeScript、Vite、TanStack Query、React Router；甘特圖自繪 SVG。
2. 色彩與字型 token 只放在全域 CSS 變數，提供亮色與暗色兩套；元件只引用變數名稱。
3. 視覺沿用互動原型的設計語彙：專業工具風、高資訊密度，字型用 Noto Sans TC，介面文字用台灣繁體中文。
4. 手機與網站兩種版面共用同一份元件（spec 8.2 平台分工）。
5. 收到 `STALE_VERSION` 一律重新載入，讓使用者重做。
6. 新畫面依序走 `grilling` → `prototype` → `/tdd` → `/code-review`。只有畫面類型第一次出現時才做 3 版 prototype，放在 `.scratch/prototypes/`，用完就丟。

## Git 與 PR

- 目前只在本機，尚未建立 git repo；何時 `git init` 與上傳 GitHub 由使用者指示。
- 一個 PR 對應 todo 的一組任務（不超過半個 Phase），標題寫任務與 AC 編號，例如 `[2.1–2.2] write_event 與樂觀鎖（AC-57）`。
- 合併條件與審查配對見 todo 5.8。

## 待裁定

| 項目 | 影響 |
| --- | --- |
| Dev-A 的決定紀錄 DA-01～DA-25（PostgreSQL 版 DDL、契約新增、規格歧義） | `docs/decisions.md`；交接重點見 `docs/dev-a-handoff.md` |
| 衡量值缺口：週報對帳結果、每日確認時間無法從資料算出 | `docs/metrics.md`；Phase 7、10 |
| spec 9.1 的 D-01、D-03 至 D-07 | 見 todo第 3 節 |
