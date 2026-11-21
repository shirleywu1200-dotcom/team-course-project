-- 個人大總管 APP — 單機 demo 範例資料種子
-- 全部虛構（範例資料，不含任何真實客戶/學員/個資）。用法：alembic upgrade head 之後，
--   psql "$G4_DATABASE_URL" -f scripts/demo_seed.sql
-- 情境：一位數位轉型顧問的一週。涵蓋：專案清單、甘特、今日、收件匣、歷程、目標、週報。
-- 系統種子（settings id=1、rubrics version=0 id=1）已由遷移 0003 建好，本檔不重插。

-- 設定：週報對象、確認時間（示範用）
UPDATE settings SET report_audience = 'manager', confirm_time = '18:00' WHERE id = 1;

-- 專案：兩個工作、一個私人（示範私人排除）
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (1, '客戶 ERP 導入', 'work', 'manager', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00'),
  (2, '新課程開發',   'work', 'manager', '2026-11-03T09:00+08:00', '2026-11-03T09:00+08:00'),
  (3, '個人健康',     'private', 'none', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00');
SELECT setval(pg_get_serial_sequence('projects', 'id'), 100);

-- 目標：成長型（件數）＋時間型（分鐘/週）
INSERT INTO goals (id, type, title, period, definition, target, energy_plan, project_id, created_at, archived_at) VALUES
  (1, 'growth', '本季完成 20 場顧問會談', '2026Q4', '每場留下紀要與行動項', 20, 'high', NULL, '2026-10-01T09:00+08:00', NULL),
  (2, 'time',   '每週深度工作 300 分鐘',  '2026Q4', '不受打擾的專注時段',   300, 'high', NULL, '2026-10-01T09:00+08:00', NULL);
SELECT setval(pg_get_serial_sequence('goals', 'id'), 100);

-- 任務：跨專案、跨狀態；含改期、卡住、單點任務、已完成（給目標統計與週報用）
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, status, done_date,
                   blocked, done_when, expected_stars, goal_id, version, created_at, updated_at) VALUES
  (1, 1, '需求訪談彙整',   '我',   'work', '2026-11-04', '2026-11-10', '2026-11-10', 'done',  '2026-11-10', false, '訪談紀要完成', 4, 1, 2, '2026-11-04T09:00+08:00', '2026-11-10T17:00+08:00'),
  (2, 1, '系統參數設定',   '小薇', 'work', '2026-11-10', '2026-11-20', '2026-11-20', 'doing', NULL,         false, '', 3, NULL, 3, '2026-11-10T09:00+08:00', '2026-11-18T10:00+08:00'),
  (3, 1, '教育訓練場次',   '我',   'work', '2026-11-12', '2026-11-21', '2026-11-24', 'todo',  NULL,         false, '', 3, NULL, 2, '2026-11-12T09:00+08:00', '2026-11-18T10:00+08:00'),
  (4, 1, '上線驗收',       '我',   'work', '2026-11-18', '2026-11-26', '2026-11-26', 'todo',  NULL,         true,  '', 3, NULL, 1, '2026-11-18T09:00+08:00', '2026-11-18T09:00+08:00'),
  (5, 2, '課程大綱定稿',   '我',   'work', '2026-11-05', '2026-11-12', '2026-11-12', 'done',  '2026-11-12', false, '大綱 5 單元', 4, 1, 2, '2026-11-05T09:00+08:00', '2026-11-12T17:00+08:00'),
  (6, 2, '投影片製作',     '阿德', 'work', '2026-11-13', '2026-11-22', '2026-11-22', 'doing', NULL,         false, '', 3, NULL, 2, '2026-11-13T09:00+08:00', '2026-11-19T10:00+08:00'),
  (7, 3, '健身房運動',     '我',   'private', '2026-11-01', '2026-11-15', '2026-11-15', 'done', '2026-11-16', false, '', 3, NULL, 2, '2026-11-01T09:00+08:00', '2026-11-16T20:00+08:00'),
  (8, NULL, '更新個人網站', '我',  'work', '2026-11-15', '2026-11-23', '2026-11-23', 'todo',  NULL,         false, '', 3, NULL, 1, '2026-11-15T09:00+08:00', '2026-11-15T09:00+08:00'),
  (9, 1, '第一次需求會談', '我',   'work', '2026-10-20', '2026-10-21', '2026-10-21', 'done',  '2026-10-21', false, '', 4, 1, 2, '2026-10-20T09:00+08:00', '2026-10-21T17:00+08:00'),
  (10,2, '試教回饋會談',   '我',   'work', '2026-10-28', '2026-10-29', '2026-10-29', 'done',  '2026-10-30', false, '', 3, 1, 2, '2026-10-28T09:00+08:00', '2026-10-30T17:00+08:00');
SELECT setval(pg_get_serial_sequence('tasks', 'id'), 100);

-- 完成回報（給已完成且關聯目標的任務；供目標統計 avg_actual 用）
INSERT INTO completion_feedback (id, task_id, actual_stars, energy, invest_vs_expected, overdue_days, rubric_id, created_at) VALUES
  (1, 1, 4, 'high', 'as_expected', 0, 1, '2026-11-10T17:00+08:00'),
  (2, 5, 4, 'mid',  'as_expected', 0, 1, '2026-11-12T17:00+08:00'),
  (3, 9, 5, 'high', 'less',        0, 1, '2026-10-21T17:00+08:00'),
  (4, 10,3, 'mid',  'more',        1, 1, '2026-10-30T17:00+08:00');
SELECT setval(pg_get_serial_sequence('completion_feedback', 'id'), 100);

-- 批次（任務 3 的改期來自整批順延示範，可選）
INSERT INTO batches (id, project_id, days, reason, note, task_count, created_at) VALUES
  (1, 1, 3, '客戶場地調整', NULL, 1, '2026-11-18T10:00+08:00');
SELECT setval(pg_get_serial_sequence('batches', 'id'), 100);

-- 收件匣：兩則來源、三個待確認候選（延期、完成、待釐清）
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
  (1, 'paste', '客戶窗口', '10:12', '教育訓練那場我們想延到 11/24', 'demo-h1', now(), now() + interval '30 days'),
  (2, 'paste', '小薇',     '10:30', '系統參數設定我已經在做了', 'demo-h2', now(), now() + interval '30 days');
SELECT setval(pg_get_serial_sequence('sources', 'id'), 100);

INSERT INTO candidates (id, source_id, kind, certainty, task_id, project_id, proposed, suggest, note, state, created_at) VALUES
  (1, 1, 'delay', 'sure',       3, 1, '{"new_due":"2026-11-24"}', NULL, NULL, 'open', now()),
  (2, 2, 'done',  'to_clarify', 2, 1, NULL, NULL, '像是進行中而非完成，你判斷。', 'open', now());
SELECT setval(pg_get_serial_sequence('candidates', 'id'), 100);

-- 歷程事件（只增）：匯入基準、改期、狀態、目標關聯、完成回報
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, origin_ref,
                    delta_days, mark, mine, batch_id) VALUES
  -- 任務 3 改期（整批順延 +3）
  (301, '2026-11-18T10:00+08:00', 1, 3, '教育訓練場次', 'due', 'latest_due', '2026-11-21', '2026-11-24', 'bulk', 1, 3, NULL, true, 1),
  -- 任務 2 狀態 todo→doing
  (302, '2026-11-18T10:00+08:00', 1, 2, '系統參數設定', 'status', 'status', 'todo', 'doing', 'manual', NULL, NULL, NULL, false, NULL),
  -- 目標關聯：1、5、9、10 → 目標 1
  (303, '2026-11-11T09:00+08:00', 1, 1, '需求訪談彙整', 'goal', 'goal_id', NULL, '1', 'manual', NULL, NULL, NULL, true, NULL),
  (304, '2026-11-13T09:00+08:00', 2, 5, '課程大綱定稿', 'goal', 'goal_id', NULL, '1', 'manual', NULL, NULL, NULL, true, NULL),
  (305, '2026-10-22T09:00+08:00', 1, 9, '第一次需求會談', 'goal', 'goal_id', NULL, '1', 'manual', NULL, NULL, NULL, true, NULL),
  (306, '2026-10-31T09:00+08:00', 2, 10, '試教回饋會談', 'goal', 'goal_id', NULL, '1', 'manual', NULL, NULL, NULL, true, NULL),
  -- 完成回報事件
  (307, '2026-11-10T17:00+08:00', 1, 1, '需求訪談彙整', 'feedback', 'actual_stars', NULL, '4', 'manual', 1, NULL, NULL, true, NULL),
  (308, '2026-11-12T17:00+08:00', 2, 5, '課程大綱定稿', 'feedback', 'actual_stars', NULL, '4', 'manual', 2, NULL, NULL, true, NULL);
SELECT setval(pg_get_serial_sequence('events', 'id'), 1000);

-- 週報（一週；示範已產生初稿）
INSERT INTO reports (id, kind, period_start, ai_draft, manual_text, excluded_private, created_at, updated_at, ai_items, ai_status) VALUES
  (1, 'weekly', '2026-11-16',
   '本週完成：需求訪談彙整。進行中：系統參數設定、投影片製作。延期：教育訓練場次改到 11/24。下週重點：上線驗收。',
   NULL, 1, '2026-11-20T18:00+08:00', '2026-11-20T18:00+08:00',
   '[{"section":"done","task_id":1,"event_id":307},{"section":"delay","task_id":3,"event_id":301}]', 'ok');
SELECT setval(pg_get_serial_sequence('reports', 'id'), 100);
