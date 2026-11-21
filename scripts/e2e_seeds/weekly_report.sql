-- 13.1 流程 09：週報已有「AI 曾經成功」的存檔（docs/dev-b/13-1-slice3-sdd.md Q1-A）。全部虛構。
-- 要接在 weekly.sql 之後灌：resetDb("scripts/e2e_seeds/weekly.sql", "scripts/e2e_seeds/weekly_report.sql")。
-- 讀取時後端用 ai_items 對目前歷程重新對帳（weekly_service._view），所以不必開 AI。
-- 11/09 週：每一項都對得上 weekly.sql 的事件 → validated=true，顯示初稿。
-- 11/02 週：延期項指向不存在的事件 299 → validated=false，改列事件清單（AC-49）。
INSERT INTO reports (id, kind, period_start, ai_draft, manual_text, excluded_private, created_at, updated_at,
                     ai_items, ai_status) VALUES
  (1, 'weekly', '2026-11-09',
   '本週完成：場地合約簽回。延期：邀請函設計改到 11/14。下週重點：報名表單上線。',
   NULL, 1, '2026-11-15T18:00+08:00', '2026-11-15T18:00+08:00',
   '[{"section": "done", "task_id": 11, "event_id": 201},
     {"section": "delay", "task_id": 13, "event_id": 212},
     {"section": "next", "task_id": 22, "event_id": null}]', 'ok'),
  (2, 'weekly', '2026-11-02',
   '延期：邀請函設計（這段不該顯示）。',
   NULL, 0, '2026-11-08T18:00+08:00', '2026-11-08T18:00+08:00',
   '[{"section": "delay", "task_id": 13, "event_id": 299}]', 'ok');
SELECT setval(pg_get_serial_sequence('reports', 'id'), 100);
