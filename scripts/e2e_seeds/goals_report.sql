-- 13.1 第四片第二段：目標 1 已有「AI 曾經成功」的回報存檔（docs/dev-b/13-1-slice4-sdd.md Q2-A）。全部虛構。
-- 要接在 goals.sql 之後灌：resetDb("scripts/e2e_seeds/goals.sql", "scripts/e2e_seeds/goals_report.sql")。
-- 讀取時後端拿 ai_items（[{key, value}]，0006）對目前統計重跑 R3（goal_report_service._validated），所以不必開 AI。
-- figures 與 goals.sql 目標 1 的統計一致：linked 2、avg_actual 3.5、overdue_count 1、progress_pct 67 → validated=true。
-- 草稿裡的數字只有 2、3.5、1、67，都在允許名單；不提私人任務 42 的標題。
-- 流程 11a 把 51 關聯進來後 linked 變 3 → 對不上 → validated=false（11d）。
INSERT INTO reports (id, kind, goal_id, ai_draft, manual_text, excluded_private, created_at, updated_at,
                     ai_items, ai_status) VALUES
  (1, 'goal', 1,
   '本季已關聯 2 件完成事件，平均實際星數 3.5，逾期 1 件，進度 67%。相關工作：視窗函式練習題。',
   NULL, 1, '2026-11-19T18:00+08:00', '2026-11-19T18:00+08:00',
   '[{"key": "linked", "value": 2}, {"key": "avg_actual", "value": 3.5},
     {"key": "overdue_count", "value": 1}, {"key": "progress_pct", "value": 67}]', 'ok');
SELECT setval(pg_get_serial_sequence('reports', 'id'), 100);
