-- 13.1 第四片：目標頁種子（docs/dev-b/13-1-slice4-sdd.md）。全部虛構。
-- 目標 1「學會 SQL 視窗函式」（growth，target 3，預期精力高）：已關聯 41（工作）、42（私人）。
--   統計：linked 2、avg_actual 3.5、avg_expected 3.0、overdue_count 1、energy 高 1／中 1、progress「2 ／ 3 件完成事件」67%。
--   流程 11a 把 51 關聯到目標 1 後：linked 3、avg_actual 4.0、avg_expected 3.3、overdue_count 1、高 2／中 1、「3 ／ 3 件完成事件」100%。
-- 目標 2「帶新人上手」（growth，target 10，預期精力中）：已關聯 61～65，精力 中 3／高 1／低 1 → 判讀「一致」（AC-46）。
-- 目標 3「每週深度工作」（time，預期精力高）：沒有關聯（第二段 11b 用）。
-- 待關聯：51「報表查詢改寫」、52「整理會議室」：done、有完成回報、從來沒有 goal_id 事件。
-- 已關聯的任務都要有 field='goal_id' 的 goal 事件，否則會被當成「沒做過關聯決定」出現在待關聯清單。
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (1, '數據平台維運', 'work', 'manager', '2026-10-01T09:00+08:00', '2026-10-01T09:00+08:00'),
  (2, '個人事務', 'private', 'none', '2026-10-01T09:00+08:00', '2026-10-01T09:00+08:00');
SELECT setval(pg_get_serial_sequence('projects', 'id'), 100);

INSERT INTO goals (id, type, title, period, definition, target, energy_plan, project_id, created_at, archived_at) VALUES
  (1, 'growth', '學會 SQL 視窗函式', '2026Q4', '', 3, 'high', NULL, '2026-10-01T09:00+08:00', NULL),
  (2, 'growth', '帶新人上手', '2026Q4', '', 10, 'mid', NULL, '2026-10-01T09:00+08:00', NULL),
  (3, 'time', '每週深度工作', '2026Q4', '', 300, 'high', NULL, '2026-10-01T09:00+08:00', NULL);
SELECT setval(pg_get_serial_sequence('goals', 'id'), 100);

INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, status, done_date,
                   expected_stars, goal_id, version, created_at, updated_at) VALUES
  (41, 1, '視窗函式練習題', '我', 'work', '2026-11-01', '2026-11-05', '2026-11-05', 'done', '2026-11-05', 3, 1, 3, '2026-11-01T09:00+08:00', '2026-11-05T17:00+08:00'),
  (42, 2, '健身課程報名', '我', 'private', '2026-11-01', '2026-11-10', '2026-11-10', 'done', '2026-11-12', 3, 1, 3, '2026-11-01T09:00+08:00', '2026-11-12T17:00+08:00'),
  (51, 1, '報表查詢改寫', '我', 'work', '2026-11-10', '2026-11-18', '2026-11-18', 'done', '2026-11-18', 4, NULL, 2, '2026-11-10T09:00+08:00', '2026-11-18T17:00+08:00'),
  (52, 1, '整理會議室', '我', 'work', '2026-11-10', '2026-11-17', '2026-11-17', 'done', '2026-11-17', 3, NULL, 2, '2026-11-10T09:00+08:00', '2026-11-17T17:00+08:00'),
  (61, 1, '新人環境建置', '我', 'work', '2026-10-05', '2026-10-06', '2026-10-06', 'done', '2026-10-06', 3, 2, 3, '2026-10-05T09:00+08:00', '2026-10-06T17:00+08:00'),
  (62, 1, '新人帳號申請', '我', 'work', '2026-10-05', '2026-10-07', '2026-10-07', 'done', '2026-10-07', 3, 2, 3, '2026-10-05T09:00+08:00', '2026-10-07T17:00+08:00'),
  (63, 1, '新人第一週導讀', '我', 'work', '2026-10-05', '2026-10-09', '2026-10-09', 'done', '2026-10-09', 3, 2, 3, '2026-10-05T09:00+08:00', '2026-10-09T17:00+08:00'),
  (64, 1, '新人程式碼審查', '我', 'work', '2026-10-12', '2026-10-16', '2026-10-16', 'done', '2026-10-16', 3, 2, 3, '2026-10-12T09:00+08:00', '2026-10-16T17:00+08:00'),
  (65, 1, '新人一對一面談', '我', 'work', '2026-10-19', '2026-10-23', '2026-10-23', 'done', '2026-10-23', 3, 2, 3, '2026-10-19T09:00+08:00', '2026-10-23T17:00+08:00');
SELECT setval(pg_get_serial_sequence('tasks', 'id'), 100);

INSERT INTO completion_feedback (task_id, actual_stars, energy, overdue_days, rubric_id, created_at)
SELECT v.task_id, v.actual_stars, v.energy, v.overdue_days, r.id, v.created_at::timestamptz
  FROM (VALUES
    (41, 4, 'high', 0, '2026-11-05T17:00+08:00'),
    (42, 3, 'mid',  2, '2026-11-12T17:00+08:00'),
    (51, 5, 'high', 0, '2026-11-18T17:00+08:00'),
    (52, 3, 'low',  0, '2026-11-17T17:00+08:00'),
    (61, 3, 'mid',  0, '2026-10-06T17:00+08:00'),
    (62, 3, 'mid',  0, '2026-10-07T17:00+08:00'),
    (63, 3, 'mid',  0, '2026-10-09T17:00+08:00'),
    (64, 3, 'high', 0, '2026-10-16T17:00+08:00'),
    (65, 3, 'low',  0, '2026-10-23T17:00+08:00')
  ) AS v(task_id, actual_stars, energy, overdue_days, created_at)
  CROSS JOIN (SELECT id FROM rubrics WHERE version = 0) r;

INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin,
                    delta_days, mark, mine, reason, note, source_id, extra, ref_event_id) VALUES
  (301, '2026-11-05T18:00+08:00', 1, 41, '視窗函式練習題', 'goal', 'goal_id', NULL, '1', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (302, '2026-11-12T18:00+08:00', 2, 42, '健身課程報名', 'goal', 'goal_id', NULL, '1', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (311, '2026-10-06T18:00+08:00', 1, 61, '新人環境建置', 'goal', 'goal_id', NULL, '2', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (312, '2026-10-07T18:00+08:00', 1, 62, '新人帳號申請', 'goal', 'goal_id', NULL, '2', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (313, '2026-10-09T18:00+08:00', 1, 63, '新人第一週導讀', 'goal', 'goal_id', NULL, '2', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (314, '2026-10-16T18:00+08:00', 1, 64, '新人程式碼審查', 'goal', 'goal_id', NULL, '2', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (315, '2026-10-23T18:00+08:00', 1, 65, '新人一對一面談', 'goal', 'goal_id', NULL, '2', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL);
SELECT setval(pg_get_serial_sequence('events', 'id'), 1000);
