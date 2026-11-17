-- 12.7 匯入走查種子：一個工作專案、一個私人專案（私人範圍 preview 不送 AI）。
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (1, '行銷活動 Q4', 'work', 'manager', now(), now()),
  (2, '家裡裝修', 'private', 'none', now(), now());
SELECT setval(pg_get_serial_sequence('projects', 'id'), 100);
