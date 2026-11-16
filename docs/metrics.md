# 衡量值埋點檢查（todo 13.8，資料面）

檢查 spec 1.3 的五個衡量值能不能只靠資料庫算出來。查詢寫在 `backend/app/db/repo/metrics_repo.py`，測試在 `backend/tests/unit/test_metrics_queries.py`，已在 PostgreSQL 17 上通過。

這份是 Dev-A 的資料面檢查。用兩週真實試用資料驗算是 QC-2 的工作（todo 5.5）。

| # | 衡量值（spec 1.3） | 可否計算 | 算法 |
| --- | --- | --- | --- |
| 1 | 週報中每個延期與完成 100% 對得上歷程事件 | **不行** | 見下方缺口 1 |
| 2 | 每日確認時間不超過上限 | **只能近似** | 每天第一筆到最後一筆候選處理的分鐘數（`daily_confirm_span_minutes`），只能當上限參考 |
| 3 | 候選確認率（含修改後確認）≥ 70% | 可以 | `candidates.state`：confirmed ÷（confirmed＋ignored）；`open` 不計 |
| 4 | 我的日期調整，註記完成率 ≥ 80% | 可以 | mine、`delta_days≠0` 的 `due` 事件中，有效註記非空的比例 |
| 5 | 完成事件中，完成回報填寫率 ≥ 70% | 可以 | 已完成任務中有 `completion_feedback` 的比例 |

## 缺口

1. **週報對帳結果沒有存下來** 【待複核：規格缺口】
   - `reports` 表沒有 `validated` 欄位，也沒有存初稿每一項對應的 `event_id`（spec 5.14 的 `items` 只在回應中出現）。
   - 建議：Dev-C 做 Phase 10 時，新增遷移，在 `reports` 加 `validated BOOLEAN` 與 `items JSONB`。DDL 擁有者是 Dev-A，遷移由 Dev-A 審。
2. **每日確認的實際使用時間沒有欄位** 【待複核：規格缺口】
   - FR-INB-16 要求「記錄實際使用時間供校正」，但 spec 第 4 章沒有對應的表。
   - 建議：Dev-B 做 Phase 7 時，新增 `confirm_sessions(started_at, ended_at, decided_count)`，由前端開始與結束收件匣確認時回報。
3. **衡量值 3 的「修改後確認」** 要從 `ai_feedback.outcome='edited'` 區分。目前比率已經把它算在 confirmed 裡；若要分開看，Dev-B 在 Phase 7.8 要確保修改後確認也寫入 `ai_feedback`。
