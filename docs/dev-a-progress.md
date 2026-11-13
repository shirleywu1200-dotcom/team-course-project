# Dev-A 進度

依 `docs/todo.md` 第 5.2 節 Dev-A 範圍。決定紀錄見 `docs/decisions.md`，交接見 `docs/dev-a-handoff.md`。

狀態說明：「單元測試綠」是指 Dev 自己的測試在 PostgreSQL 17 上通過。todo 的完成定義還需要 QC 驗收測試轉綠，所以 todo 只標 `[~]`。

## 環境與指令

- **PostgreSQL**：Docker 容器 `g4-pg`（`postgres:17`），只綁 `127.0.0.1:54329`，帳號 `g4`。
  - 啟動 `docker start g4-pg`；停止 `docker stop g4-pg`；移除 `docker rm -f g4-pg`。
- **後端**：在 `backend/` 下執行。
  - 安裝 `uv sync`
  - 遷移 `.venv/bin/alembic upgrade head`
  - 測試 `.venv/bin/pytest`
  - 檢查 `.venv/bin/ruff check .`
  - 啟動 `.venv/bin/python -m app.main`
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

- 後端 pytest：202 個通過（約 17 秒），含 todo 6.2 的契約保護測試（`test_contract_guards.py`）與 log 不含使用者內容的測試。
- 前端 Vitest：18 個通過。
- ruff：無問題。
- 前端 tsc：無錯誤。
