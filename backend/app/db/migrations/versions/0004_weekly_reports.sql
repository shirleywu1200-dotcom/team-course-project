-- 0004 週報存檔（2026-11-16 產品負責人裁定，#18 第 1 點 (b)；FR-RPT-03、04）
-- 只新增欄位與索引，不改既有欄位。

-- AI 回傳的結構化項目：GET 時用它對目前的歷程重新對帳（R4）
ALTER TABLE reports ADD COLUMN ai_items JSONB;

-- 產生初稿時的 AI 狀態（spec 5.3）；尚未呼叫過 AI 為 NULL
ALTER TABLE reports ADD COLUMN ai_status TEXT
  CHECK (ai_status IS NULL OR ai_status IN ('ok','unavailable','invalid_output'));

-- 每週一列；目標回報（kind='goal'）不受影響
CREATE UNIQUE INDEX reports_weekly_period_uq ON reports (period_start) WHERE kind = 'weekly';

-- 週報列一定要有週次：NULL 不受唯一索引約束，不擋的話「每週一列」會被繞過（#18 J8）
ALTER TABLE reports ADD CONSTRAINT reports_weekly_period_check
  CHECK (kind <> 'weekly' OR period_start IS NOT NULL);
