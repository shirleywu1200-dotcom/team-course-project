# QC 驗收測試（QC-1／QC-2 維護）

這個資料夾放依 spec 第 7 章 AC 寫的驗收測試，由 QC 撰寫與持有；Dev 只能執行，不修改（todo 5.1）。

- 檔名建議：`test_ac<編號>_<簡述>.py`，測試名稱帶 AC 編號，方便 13.2 驗收總表對照。
- 只依 spec 與對外契約（DDL、OpenAPI、函式簽名）撰寫，不讀 `app/` 的實作。
- 可直接使用 `tests/conftest.py` 的夾具：`db`（每個測試一個獨立資料庫）、`seed`、`client`、`clock`、`ai`、`query`。
- FR-AI-06 防回歸測試（todo 3.5、7.9、9.4、12.2）放這裡，任何人不得刪除或放寬。

目前尚未有驗收測試。Dev-A 的單元測試在 `tests/unit/`，不能取代本資料夾的驗收。
