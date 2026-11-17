# QC 驗收測試（QC-1／QC-2 維護）

這個資料夾放依 spec 第 7 章 AC 寫的驗收測試，由 QC 撰寫與持有；Dev 只能執行，不修改（todo 5.1）。

- 檔名建議：`test_ac<編號>_<簡述>.py`，測試名稱帶 AC 編號，方便 13.2 驗收總表對照。
- 只依 spec 與對外契約（DDL、OpenAPI、函式簽名）撰寫，不讀 `app/` 的實作。
- 可直接使用 `tests/conftest.py` 的夾具：`db`（每個測試一個獨立資料庫）、`seed`、`client`、`clock`、`ai`、`query`。
- FR-AI-06 防回歸測試（todo 3.5、7.9、9.4、12.2）放這裡，任何人不得刪除或放寬。

Dev-A 的單元測試在 `tests/unit/`，不能取代本資料夾的驗收。

- 2026-11-16：QC-2 帳號未定前，產品負責人裁定由 Dev-B 自補 Phase 5～8 的驗收測試（PR #20），QC 帳號確定後移交複核。撰寫者只讀 spec、OpenAPI、DDL 與本資料夾，不讀 `app/`；清單先經獨立審查，紀錄在 PR #20 留言。
- 測試可直接使用的程式介面（視為契約）：`app.ai.client` 的例外類別、`app.clock`、`app.scheduler.run_once(db)`、`app.worker.run_once(db, ai)`、`app.worker.reset_running(db)`。AI 節點的 payload 與輸出格式見 spec 5.3a。
- 待裁定的斷言以 `pytest.mark.xfail(reason="待裁定 Qn")` 標示；裁定後移除標記。
