-- 0004 候選記住收件時的專案（PR #20 審查 B5；2026-11-16 產品負責人裁定，FR-INB-14）
-- 只新增欄位與索引，不改既有欄位。NULL 表示收件時沒有指定專案。

ALTER TABLE candidates ADD COLUMN project_id BIGINT REFERENCES projects(id);

-- 新增外鍵時同一個遷移建索引（PostgreSQL 不會自動建）
CREATE INDEX ix_candidates_project ON candidates(project_id);
