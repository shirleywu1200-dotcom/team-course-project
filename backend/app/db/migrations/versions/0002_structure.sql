-- 0002 結構變更（PR #1 審查 A1、B5；2026-11-15 產品負責人裁定）

-- A1：AI-08 已取消，ai_runs.node_id 不再接受
ALTER TABLE ai_runs DROP CONSTRAINT ai_runs_node_id_check;
ALTER TABLE ai_runs ADD CONSTRAINT ai_runs_node_id_check
  CHECK (node_id IN ('AI-01','AI-02','AI-03','AI-04','AI-05','AI-06','AI-07'));

-- B5：量表版本確認後不可修改（FR-RUB-01）。UPDATE、DELETE、TRUNCATE 皆擋；INSERT 不受影響。
-- settings 不加：啟用精靈需要 UPDATE 那一列。
CREATE FUNCTION rubrics_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'rubrics are immutable' USING ERRCODE = 'restrict_violation';
END;
$$;
CREATE TRIGGER rubrics_no_update BEFORE UPDATE ON rubrics
  FOR EACH ROW EXECUTE FUNCTION rubrics_immutable();
CREATE TRIGGER rubrics_no_delete BEFORE DELETE ON rubrics
  FOR EACH ROW EXECUTE FUNCTION rubrics_immutable();
CREATE TRIGGER rubrics_no_truncate BEFORE TRUNCATE ON rubrics
  FOR EACH STATEMENT EXECUTE FUNCTION rubrics_immutable();
