-- AI-05 週報端對端種子（docs/dev-b/ai-05-sdd.md 驗收第 3 點）。全部虛構。
-- 本週 2026-11-09（一）～11-15（日）。呼叫：POST /api/v1/reports/weekly/draft {"week_start": "2026-11-09"}
-- 預期：done 2 筆、delay 2 筆（任務 13 兩筆事件）、next 3 筆（13 已逾期、21 卡住、22 下週到期）；
-- 私人任務 31（「牙醫回診」）本週完成但不送 AI → excluded_private=1，draft 不可出現「牙醫回診」。
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (1, '年終活動', 'work', 'manager', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00'),
  (2, '個人事務', 'private', 'none', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00');
SELECT setval(pg_get_serial_sequence('projects', 'id'), 100);

INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due,
                   status, done_date, blocked, done_when, version, created_at, updated_at) VALUES
  (11, 1, '場地合約簽回', '阿德', 'work', '2026-11-01', '2026-11-11', '2026-11-11', 'done', '2026-11-11', false, '', 2, '2026-11-01T09:00+08:00', '2026-11-11T17:00+08:00'),
  (12, 1, '贊助商名單確認', '我', 'work', '2026-11-01', '2026-11-13', '2026-11-13', 'done', '2026-11-13', false, '', 2, '2026-11-01T09:00+08:00', '2026-11-13T17:00+08:00'),
  (13, 1, '邀請函設計', '小薇', 'work', '2026-11-01', '2026-11-10', '2026-11-14', 'doing', NULL, false, '', 3, '2026-11-01T09:00+08:00', '2026-11-12T10:00+08:00'),
  (14, 1, '餐飲廠商比價', '老周', 'work', '2026-11-01', '2026-11-12', '2026-11-26', 'todo', NULL, false, '', 2, '2026-11-01T09:00+08:00', '2026-11-11T10:00+08:00'),
  (21, 1, '音響設備租借', '阿德', 'work', '2026-11-01', '2026-12-05', '2026-12-05', 'todo', NULL, true, '', 2, '2026-11-01T09:00+08:00', '2026-11-12T10:00+08:00'),
  (22, 1, '報名表單上線', '我', 'work', '2026-11-01', '2026-11-19', '2026-11-19', 'doing', NULL, false, '', 1, '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00'),
  (31, 2, '牙醫回診', '我', 'private', '2026-11-01', '2026-11-12', '2026-11-12', 'done', '2026-11-12', false, '', 2, '2026-11-01T09:00+08:00', '2026-11-12T17:00+08:00');
SELECT setval(pg_get_serial_sequence('tasks', 'id'), 100);

INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin,
                    delta_days, mark, mine, reason, note, source_id, extra, ref_event_id) VALUES
  (201, '2026-11-11T17:00+08:00', 1, 11, '場地合約簽回', 'status', 'status', 'doing', 'done', 'manual', NULL, NULL, true, NULL, NULL, NULL, '{"done_date": "2026-11-11"}', NULL),
  (202, '2026-11-13T17:00+08:00', 1, 12, '贊助商名單確認', 'status', 'status', 'doing', 'done', 'manual', NULL, NULL, true, NULL, NULL, NULL, '{"done_date": "2026-11-13"}', NULL),
  (211, '2026-11-10T10:00+08:00', 1, 13, '邀請函設計', 'due', 'latest_due', '2026-11-10', '2026-11-12', 'manual', 2, NULL, false, NULL, NULL, NULL, NULL, NULL),
  (212, '2026-11-12T10:00+08:00', 1, 13, '邀請函設計', 'due', 'latest_due', '2026-11-12', '2026-11-14', 'manual', 2, NULL, false, NULL, NULL, NULL, NULL, NULL),
  (213, '2026-11-11T10:00+08:00', 1, 14, '餐飲廠商比價', 'due', 'latest_due', '2026-11-12', '2026-11-26', 'manual', 14, NULL, false, NULL, NULL, NULL, NULL, NULL),
  (221, '2026-11-12T10:00+08:00', 1, 21, '音響設備租借', 'status', 'blocked', 'false', 'true', 'manual', NULL, NULL, false, NULL, NULL, NULL, NULL, NULL),
  (231, '2026-11-12T17:00+08:00', 2, 31, '牙醫回診', 'status', 'status', 'todo', 'done', 'manual', NULL, NULL, true, NULL, NULL, NULL, '{"done_date": "2026-11-12"}', NULL);
SELECT setval(pg_get_serial_sequence('events', 'id'), 1000);
