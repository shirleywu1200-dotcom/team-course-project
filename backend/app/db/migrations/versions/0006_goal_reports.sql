-- 0006 目標回報存檔（2026-11-20 產品負責人裁定，#47、#86；spec 5.13「目標回報」第 1 點；FR-GOL-06、07）
-- 只新增索引與 CHECK，不改既有欄位。ai_items 存驗證後的 figures（[{key, value}]）。

-- 每個目標一列
CREATE UNIQUE INDEX reports_goal_uq ON reports (goal_id) WHERE kind = 'goal';

-- 目標回報列一定要有 goal_id：NULL 不受唯一索引約束（比照 0005，#18 J8）
ALTER TABLE reports ADD CONSTRAINT reports_goal_id_check
  CHECK (kind <> 'goal' OR goal_id IS NOT NULL);
