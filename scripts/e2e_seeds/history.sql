-- 13.1 流程 10：歷程篩選（12.6；docs/dev-b/13-1-slice3-sdd.md）。全部虛構。
-- 專案 1「年終活動」：due 4 筆（301～303 同一批次 1、304 單筆）＋ status 1 筆 → 專案 1 共 5 筆。
-- 專案 2「產品發表」：due 1 筆（306）。單點任務 5：due 1 筆（307，project_id 為 NULL；AC-05）。
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (1, '年終活動', 'work', 'manager', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00'),
  (2, '產品發表', 'work', 'manager', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00');
SELECT setval(pg_get_serial_sequence('projects', 'id'), 100);

INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due,
                   status, done_date, blocked, done_when, version, created_at, updated_at) VALUES
  (1, 1, '場地勘查', '我', 'work', '2026-11-01', '2026-11-10', '2026-11-16', 'todo', NULL, false, '', 3, '2026-11-01T09:00+08:00', '2026-11-12T10:00+08:00'),
  (2, 1, '主持人邀約', '阿德', 'work', '2026-11-01', '2026-11-11', '2026-11-14', 'todo', NULL, false, '', 2, '2026-11-01T09:00+08:00', '2026-11-12T10:00+08:00'),
  (3, 1, '流程表定稿', '小薇', 'work', '2026-11-01', '2026-11-12', '2026-11-15', 'doing', NULL, false, '', 3, '2026-11-01T09:00+08:00', '2026-11-13T10:00+08:00'),
  (4, 2, '新聞稿撰寫', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-22', 'todo', NULL, false, '', 2, '2026-11-01T09:00+08:00', '2026-11-12T10:00+08:00'),
  (5, NULL, '更新個人履歷', '我', 'work', '2026-11-01', '2026-11-18', '2026-11-21', 'todo', NULL, false, '', 2, '2026-11-01T09:00+08:00', '2026-11-12T10:00+08:00');
SELECT setval(pg_get_serial_sequence('tasks', 'id'), 100);

INSERT INTO batches (id, project_id, days, reason, note, task_count, created_at) VALUES
  (1, 1, 3, NULL, NULL, 3, '2026-11-12T10:00+08:00');
SELECT setval(pg_get_serial_sequence('batches', 'id'), 100);

INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, origin_ref,
                    delta_days, mine, batch_id) VALUES
  (301, '2026-11-12T10:00+08:00', 1, 1, '場地勘查', 'due', 'latest_due', '2026-11-13', '2026-11-16', 'bulk', 1, 3, true, 1),
  (302, '2026-11-12T10:00+08:00', 1, 2, '主持人邀約', 'due', 'latest_due', '2026-11-11', '2026-11-14', 'bulk', 1, 3, false, 1),
  (303, '2026-11-12T10:00+08:00', 1, 3, '流程表定稿', 'due', 'latest_due', '2026-11-12', '2026-11-15', 'bulk', 1, 3, false, 1),
  (304, '2026-11-10T10:00+08:00', 1, 1, '場地勘查', 'due', 'latest_due', '2026-11-10', '2026-11-13', 'manual', NULL, 3, true, NULL),
  (305, '2026-11-13T10:00+08:00', 1, 3, '流程表定稿', 'status', 'status', 'todo', 'doing', 'manual', NULL, NULL, false, NULL),
  (306, '2026-11-12T10:00+08:00', 2, 4, '新聞稿撰寫', 'due', 'latest_due', '2026-11-20', '2026-11-22', 'manual', NULL, 2, true, NULL),
  (307, '2026-11-12T10:00+08:00', NULL, 5, '更新個人履歷', 'due', 'latest_due', '2026-11-18', '2026-11-21', 'manual', NULL, 3, true, NULL);
SELECT setval(pg_get_serial_sequence('events', 'id'), 1000);
