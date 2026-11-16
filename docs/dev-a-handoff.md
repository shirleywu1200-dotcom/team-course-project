# Dev-A 交接說明

給 Dev-B、Dev-C、QC-1、QC-2 與產品負責人。契約異動與規格歧義的完整理由見 `docs/decisions.md`。

## 給產品負責人：待複核

1. **DA-01 PostgreSQL 版 DDL**：spec 4.2、6.8、8.1–8.3 與 todo 0.7、1.3、1.6 已改寫；原版是 `main` 上的 `docs/spec.md`、`docs/todo.md`，可直接看 PR 的 diff。開工會簽核 DDL 契約前請先看。
2. **DA-03～DA-25**：契約新增（`adjust_due` 兩個參數、`POST /tasks/{id}/status`、`MARK_IGNORED` 警告碼、`INTERNAL_ERROR` 錯誤碼）與規格歧義的暫定做法。
3. **`docs/metrics.md` 的兩個缺口**：週報對帳結果與每日確認時間目前無法從資料算出。
4. **`docs/platform-settings.md`**：這是私人 repo，Free 方案很可能無法強制分支保護與 CODEOWNERS；團隊已選 C（維持現狀，靠 CI 的 `path-owners` 檢查與「紅燈不合併」約定）；請各角色提供 GitHub 帳號名稱，由 Dev-A 填入 `.github/path-owners.txt`。

## 給 Dev-B

- **`adjust_due` 的簽名**多了 `origin_ref=None, source_id=None`（DA-03）。確認延期候選時請用：
  `adjust_due(conn, task_id, new_due, expected_version, None, None, None, True, origin="candidate", origin_ref=<候選 id>, source_id=<來源 id>)`
  - 原因與註記一律傳 `None`（FR-DUE-05a），`defer_mark=True`。回傳的 `needs_mark` 就是 spec 5.11 的 `needs_mark`（DA-04）。
- **確認完成與卡住候選、從待配對候選建立任務**：`app/domain/tasks.py` 的 `complete_task`、`set_blocked`、`create_task` 都接受 `origin`、`origin_ref`、`source_id`（`create_task` 為 Issue #2 新增，預設 `origin="manual"`）。
- **`AIClient`／`FakeAIClient`** 的骨架在 `app/ai/client.py`，契約擁有者是你，介面請你確認後凍結。
- **交易**：路由用 `db.run(lambda conn: ...)`，一個業務操作一個交易，例外即整筆回滾；死結與序列化失敗自動重試 3 次。
- **事件**：一律經 `app/domain/events.py` 的 `write_event`，不直接 INSERT `events`。
- **Phase 5**：`events_repo.mine_due_events_with_effective_mark` 已有有效註記的 SQL，可參考。`TaskRepo.delayed_count` 已實作「已延期數」。
- **`docs/metrics.md` 缺口 2**：Phase 7 請一併考慮每日確認時間的紀錄。
- **8.6「刪除所有來源原文」**：`idempotency_keys.response` 可能存有含原句的回應，清除範圍要一併處理（DA-23）。

## 給 Dev-C

- **前端暫代檔**：為了讓 12.2、12.4、12.5 能測試，Dev-A 先建了最小骨架。檔頭都標了「暫代 Dev-C todo …」，請在 0.8 與 Phase 11 時取代或吸收：

  | 暫代檔 | 對應你的任務 |
  | --- | --- |
  | `frontend/package.json`、`vite.config.ts`、`tsconfig.json` | 0.8 |
  | `src/api/types.ts`（手寫型別） | 0.8 由 OpenAPI 產生 |
  | `src/api/client.ts` | 11.2 |
  | `src/App.tsx`（路由、TokenGate） | 11.1 |
  | `src/styles/tokens.css`、`base.css`（亮暗兩套 CSS 變數） | 11.4 |
  | `src/components/standin/`（註記面板、原因下拉、錯誤橫幅） | 11.5 |
  | `src/test/server.tsx`（MSW） | 11.7 |
- **Windows 開發環境**：指令一律用 `uv run <指令>`（Mac／Linux 共用）。要直接呼叫虛擬環境時，Windows 的路徑是 `.venv\Scripts\python`（Mac／Linux 是 `.venv/bin/python`）。
- **OpenAPI 與型別產生（0.8）**：OpenAPI 在 `/api/v1/openapi.json`，需要 token；`/docs`、`/redoc` 已關閉（DA-24）。產生型別時不必啟動伺服器，在 `backend/` 下執行 `uv run python -m app.export_openapi > ../frontend/openapi.json` 即可。
- **12.3 任務詳情頁**：請把 `AdjustDuePanel`（12.2）與 `BaselineCorrectionLink`（12.5）放進去；之後 `src/features/due-adjust/TaskDuePage.tsx` 就可以刪掉。
- **Phase 10 週報**：`docs/metrics.md` 缺口 1 建議 `reports` 加 `validated` 與 `items`，需要新遷移（DDL 擁有者 Dev-A 審）。

## 給 QC-1、QC-2

- **測試環境**：`backend/tests/conftest.py` 提供每個測試一個獨立資料庫（由範本複製）、`seed()`、固定時鐘（2026-11-11 10:00）、`client`、`FakeAIClient`。
- **目錄**：
  - 驗收測試放 `backend/tests/acceptance/`。
  - 夾具庫放 `backend/tests/fixtures/`，PostgreSQL 種子的寫法注意事項見該資料夾的 README。
- **Dev 的單元測試**：在 `backend/tests/unit/`，已按 AC 編號命名，但不取代你們的驗收。
- **前端**：
  - 12.2 的 FR-AI-06 防回歸測試目前是 Dev 側版本（`AdjustDuePanel.test.tsx` 第一個測試），請另寫 QC 持有的版本。
  - Playwright 流程（12.x 完成定義）尚未建立，屬 QC-2。
- **Phase 13**：
  - 13.5、13.6 演練時，`docs/deploy.md` 第 5 節的備份與還原指令已實際跑過一次（2026-11-13，PostgreSQL 17）。
  - 13.8 的驗算請以 `docs/metrics.md` 的算法對照。
