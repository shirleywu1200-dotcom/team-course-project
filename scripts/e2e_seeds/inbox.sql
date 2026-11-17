-- 12.8 收件匣走查種子：一個專案、三個任務、四則來源與四種候選（延期、完成、待釐清、待配對）。
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (1, '會員系統 2.0 改版', 'work', 'manager', now(), now());
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, status, version,
                   created_at, updated_at) VALUES
  (2, 1, '畫面規格 v1', '我', 'work', '2026-11-09', '2026-11-13', '2026-11-13', 'todo', 1, now(), now()),
  (3, 1, 'API 介面定義', '小薇', 'work', '2026-11-09', '2026-11-12', '2026-11-15', 'doing', 1, now(), now()),
  (4, 1, '確認驗收條件', '我', 'work', '2026-11-14', '2026-11-18', '2026-11-18', 'todo', 1, now(), now());
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
  (1, 'paste', '阿德', '10:12', '畫面規格 v1 確定延到 11/20', 'e1', now(), now() + interval '30 days'),
  (2, 'paste', '小薇', '10:30', 'API 介面定義已上傳', 'e2', now(), now() + interval '30 days'),
  (3, 'paste', '客戶', '11:20', '驗收條件可能會延到 11/25', 'e3', now(), now() + interval '30 days'),
  (4, 'paste', '小薇', '10:20', '報表處理我來', 'e4', now(), now() + interval '30 days');
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, suggest, note, state, created_at) VALUES
  (21, 1, 'delay', 'sure', 2, '{"new_due":"2026-11-20"}', NULL, NULL, 'open', now()),
  (22, 2, 'done', 'sure', 3, NULL, NULL, NULL, 'open', now()),
  (23, 3, 'unclear', 'to_clarify', 4, NULL, '{"kind":"delay","new_due":"2026-11-25"}',
       '含「可能」，先不當作延期。你判斷要不要處理。', 'open', now()),
  (24, 4, 'unmatched', 'to_match', NULL, NULL, '{"kind":"done"}', '找不到對應任務，不猜。', 'open', now());
SELECT setval(pg_get_serial_sequence(t, 'id'), 100) FROM unnest(ARRAY['projects','tasks','sources','candidates']) t;
