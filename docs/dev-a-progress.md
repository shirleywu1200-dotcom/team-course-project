# Dev-A 進度

依 `docs/todo.md` 第 5.2 節 Dev-A 範圍。決定紀錄見 `docs/decisions.md`，交接見 `docs/dev-a-handoff.md`。

狀態說明：「單元測試綠」是指 Dev 自己的測試在 PostgreSQL 17 上通過。todo 的完成定義還需要 QC 驗收測試轉綠，所以 todo 只標 `[~]`。

## 環境與指令

- **PostgreSQL**：Docker 容器 `g4-pg`（`postgres:17`），帳號 `g4`。團隊範例的本機連接埠是 `5433`（`env/example.env`、`docs/deploy.md`，Issue #4）；Dev-A 本機的容器沿用 `127.0.0.1:54329`，以自己的 `env/local.env` 為準。
  - 啟動 `docker start g4-pg`；停止 `docker stop g4-pg`；移除 `docker rm -f g4-pg`。
- **後端**：在 `backend/` 下執行。
  - 安裝 `uv sync`
  - 遷移 `uv run alembic upgrade head`
  - 測試 `uv run pytest`
  - 檢查 `uv run ruff check .`
  - 啟動 `uv run python -m app.main`
- **前端**：在 `frontend/` 下執行。
  - 安裝 `npm ci`
  - 測試 `npm test`
  - 型別檢查 `npm run typecheck`
  - 開發 `npm run dev`
- **祕密**：放在 `env/local.env`（不進版控）；範例檔是 `env/example.env`。

## 進度（2026-11-13）

| 項目 | 狀態 | 驗證方式 |
| --- | --- | --- |
| PostgreSQL 提案、寫回 spec | 完成，待產品負責人複核（DA-01） | DDL 在 PostgreSQL 17 套用成功；遷移往返測試 |
| Phase 0 骨架（0.1–0.7、0.9） | 單元測試綠 | `test_phase0_skeleton.py`：每個錯誤碼格式、401、冪等、FakeAIClient、健康檢查 |
| 0.9 CI 與 pre-commit | pre-commit 已實測；**CI 未執行** | pre-commit：在暫存 git 副本實測，乾淨暫存區通過，暫存假金鑰時被擋（exit 1），commit 未產生。CI：`.github/workflows/ci.yml` 要上 GitHub 後才會跑 |
| Phase 1 資料庫（1.1–1.6） | 單元測試綠 | `test_phase1_schema.py`：44 個 CHECK 合法與非法、AC-11（UPDATE、DELETE、TRUNCATE）、遷移往返、真實 pg_dump 備份 |
| Phase 2 事件、專案、任務（2.1–2.10） | 單元測試綠 | `test_phase2_core.py`：AC-05、26、29、57 |
| Phase 3 日期調整與註記（3.1–3.9） | 單元測試綠 | `test_phase3_due.py`：AC-01–10、12、12a、13，並行測試 |
| Phase 4 整批順延與基準更正（4.1–4.9） | 單元測試綠 | `test_phase4_bulk_baseline.py`：AC-14–24、AC-25 後端部分 |
| 12.2、12.4、12.5 前端頁 | 元件測試綠，建立在暫代骨架上 | Vitest＋MSW 18 個測試；`tsc`；`vite build`；Vite 代理連到後端；以前端測試的請求本文打真實 API，8 項回應欄位比對通過。**未在真實瀏覽器操作過**；Playwright 流程屬 QC-2 |
| 13.7 部署文件 | 完成 | `docs/deploy.md`；備份與還原指令實際跑過一次 |
| 13.8 埋點檢查（資料面） | 完成，有 2 個缺口 | `docs/metrics.md`；`test_metrics_queries.py` |
| 13.5、13.6 支援 QC-1 | 等 QC-1 排演練 | — |

## 測試數字

- 後端 pytest：225 個通過（約 21 秒），含契約保護測試（簽名、錯誤碼、OpenAPI 2xx schema 非空）、log 不含使用者內容、AC-59、AC-61、AC-62。
- 前端 Vitest：18 個通過。
- ruff：無問題。
- 前端 tsc：無錯誤。

## 待辦（2026-11-15 彙整：PR #1 審查、issue、Dev-B 分支文件）

來源：PR #1 Dev-C（兼產品負責人）三則審查留言（2026-11-15）、issue #2–#5、`dev-b/phase-5-8` 的 `docs/dev-b/requests-to-dev-a.md`。

### 已完成，等其他人

- [x] issue #2 R-01、#3 R-02、#4 R-03：已在 PR #1 處理，PR 合併時自動關閉
- [x] issue #5：已讀並關閉
- [ ] path-owners：等 MoraChen、Andpeterpan 在 PR #1 按 Approve 後 Re-run

### PR #1 審查回饋（依建議順序）

- [x] **A4（高優先）** 各路由補 `response_model`，重新匯出 OpenAPI 後所有 2xx 都有非空 schema；選做：CI 檢查空 schema
- [x] **B2** 系統種子遷移（`settings` id=1、`rubrics` version=0，文字已由產品負責人確認），冪等；AC-59。同步修正 Dev-A 測試中插入 `rubrics(id=1, version=0)`、`settings(id=1)` 的種子，並通知 QC、Dev-B
- [x] **B5** `rubrics` 不可修改觸發器（UPDATE、DELETE、TRUNCATE），說明做法、成本與對 QC 測試清理的影響
- [x] **A1** 移除 `ai_runs.node_id` 的 `AI-08`（建議用新遷移，不改 0001）
- [x] **A2** `POST /tasks/{id}/adjust-start`（AC-62）；建立時開始日晚於期限回 422（AC-61，回答 B1）。先把 AC-59、61、62 與新端點、警告碼 `START_AFTER_DUE` 寫進 spec
- [x] **C** 移除 `frontend/tsconfig.tsbuildinfo` 並加入 `.gitignore`；更新 CLAUDE.md「Git 與 PR」；修 `BulkShiftPage` 偶發失敗的測試
- [~] **D2** 已在 PR #1 回覆提案（建議 `{taskId, onDone, onClose}`，拿掉 `expectedVersion`），等 Dev-C 選擇後實作
- [x] **D3** `dev-a-handoff.md` 補 Windows venv 路徑 `.venv\Scripts\python`
- 約束 **D1**：前端 18 個測試必須保持通過；**C**：之後的 PR 回到不超過半個 Phase

### 需要通知

- Dev-B：Phase 8 設計（`phase-8-sdd.md` Q1、Q3）原選「程式補預設列、不加量表觸發器」，已被產品負責人 B2、B5 裁定改為系統種子遷移與觸發器
