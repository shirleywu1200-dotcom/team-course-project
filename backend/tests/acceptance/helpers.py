"""驗收測試共用的種子與小工具（只依 spec、OpenAPI、DDL 與函式簽名，不讀實作）。"""

API = "/api/v1"

# 放進訊息原文的辨識字串：清除後用它掃所有表、回應、匯出與 log，確認沒有殘留。
MARK = "ZXQ7731"

_TS = "'2026-11-01T09:00+08:00'"

# 專案 1、3 為工作範圍，2 為私人範圍。任務 4（私人專案）、5（私人單點）、6（工作專案裡的私人任務）
# 都不該送給 AI；任務 7 已完成；任務 9 為工作範圍的單點任務。
SEED_BASE = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
 (1, '會員系統 2.0 改版', 'work', 'manager', {_TS}, {_TS}),
 (2, '家庭旅行', 'private', 'none', {_TS}, {_TS}),
 (3, '官網改版', 'work', 'client', {_TS}, {_TS});
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due,
                   status, done_date, created_at, updated_at) VALUES
 (1, 1, '畫面規格 v1', '阿德', 'work', '2026-11-09', '2026-11-13', '2026-11-13', 'todo', NULL, {_TS}, {_TS}),
 (2, 1, 'API 介面定義', '我', 'work', '2026-11-09', '2026-11-14', '2026-11-14', 'doing', NULL, {_TS}, {_TS}),
 (3, 1, '測試環境建置', '我', 'work', '2026-11-10', '2026-11-20', '2026-11-20', 'todo', NULL, {_TS}, {_TS}),
 (4, 2, '訂機票祕密行程', '我', 'private', '2026-11-10', '2026-11-20', '2026-11-20', 'todo', NULL, {_TS}, {_TS}),
 (5, NULL, '私人健檢預約', '我', 'private', '2026-11-10', '2026-11-20', '2026-11-20', 'todo', NULL, {_TS}, {_TS}),
 (6, 1, '薪資調整試算', '我', 'private', '2026-11-10', '2026-11-20', '2026-11-20', 'todo', NULL, {_TS}, {_TS}),
 (7, 1, '需求訪談', '我', 'work', '2026-11-03', '2026-11-07', '2026-11-07', 'done', '2026-11-07', {_TS}, {_TS}),
 (8, 3, '首頁文案', '小薇', 'work', '2026-11-10', '2026-11-20', '2026-11-20', 'todo', NULL, {_TS}, {_TS}),
 (9, NULL, '報帳', '我', 'work', '2026-11-10', '2026-11-20', '2026-11-20', 'todo', NULL, {_TS}, {_TS});
"""

_RCV = "'2026-11-11T09:00+08:00', '2026-12-11T09:00+08:00'"
_CT = "'2026-11-11T09:00+08:00'"

# 候選：1 延期（阿德的任務）、2 延期（我的任務）、3 卡住、4 待釐清（建議延期）、5 待配對、
# 6 完成、7 延期（對應任務已完成）、8 待釐清（建議卡住）。全部為 open。
SEED_CANDIDATES = f"""
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
 (1, 'paste', '阿德', '10:12', '畫面規格 v1 確定延到 11/18 {MARK}', 'seed-h1', {_RCV}),
 (2, 'paste', '我', '10:15', 'API 介面定義要延到 11/19 {MARK}', 'seed-h2', {_RCV}),
 (3, 'paste', '小薇', '10:20', '測試環境建置卡住了 {MARK}', 'seed-h3', {_RCV}),
 (4, 'paste', '阿德', '10:25', 'API 介面定義可能要延到 11/21 {MARK}', 'seed-h4', {_RCV}),
 (5, 'paste', '阿德', '10:30', '報表處理我來接 {MARK}', 'seed-h5', {_RCV}),
 (6, 'paste', '我', '10:35', '測試環境建置完成了 {MARK}', 'seed-h6', {_RCV}),
 (7, 'paste', '我', '10:40', '需求訪談要延到 11/25 {MARK}', 'seed-h7', {_RCV}),
 (8, 'paste', '阿德', '10:45', '畫面規格 v1 會不會卡住？ {MARK}', 'seed-h8', {_RCV});
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, suggest, state, created_at) VALUES
 (1, 1, 'delay', 'sure', 1, '{{"new_due":"2026-11-18"}}', NULL, 'open', {_CT}),
 (2, 2, 'delay', 'sure', 2, '{{"new_due":"2026-11-19"}}', NULL, 'open', {_CT}),
 (3, 3, 'stuck', 'sure', 3, NULL, NULL, 'open', {_CT}),
 (4, 4, 'unclear', 'to_clarify', 2, NULL, '{{"kind":"delay","new_due":"2026-11-21"}}', 'open', {_CT}),
 (5, 5, 'unmatched', 'to_match', NULL, NULL, NULL, 'open', {_CT}),
 (6, 6, 'done', 'sure', 3, NULL, NULL, 'open', {_CT}),
 (7, 7, 'delay', 'sure', 7, '{{"new_due":"2026-11-25"}}', NULL, 'open', {_CT}),
 (8, 8, 'unclear', 'to_clarify', 1, NULL, '{{"kind":"stuck"}}', 'open', {_CT});
"""


def ai_calls(ai, node=None):
    """回傳 FakeAIClient 記錄的 payload 清單（可只取某個節點）。"""
    out = []
    for c in ai.calls:
        if isinstance(c, dict):
            n, p = c.get("node_id", c.get("node")), c.get("payload")
        elif isinstance(c, (tuple, list)):
            n, p = c[0], c[1]
        else:
            n, p = getattr(c, "node_id", getattr(c, "node", None)), getattr(c, "payload", None)
        if node is None or n == node:
            out.append(p)
    return out


def columns(query, table):
    """資料庫裡這張表目前的欄位名稱（information_schema）。"""
    rows = query("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema = 'public' AND table_name = :t", t=table)
    return {r["column_name"] for r in rows}


def table_names(query):
    return [r["tablename"] for r in query("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")]


def tables_containing(query, needle):
    """以字串掃所有表的所有欄位（含 JSONB），回傳出現該字串的表與筆數。"""
    hits = {}
    for t in table_names(query):
        n = query(f'SELECT count(*) AS n FROM "{t}" x WHERE CAST(row_to_json(x) AS text) LIKE :p',
                  p=f"%{needle}%")[0]["n"]
        if n:
            hits[t] = n
    return hits


def count(query, table):
    return query(f'SELECT count(*) AS n FROM "{table}"')[0]["n"]


def ingest(client, text, project_id=1, **kw):
    return client.post(f"{API}/ingest", json={"text": text, "project_id": project_id}, **kw)


def lines(n, mark=""):
    """產生 n 行訊息（每行不同時間與內容）。"""
    return "\n".join(f"[{10 + i // 60:02d}:{i % 60:02d}] 阿德：第 {i + 1} 項進度正常 {mark}".rstrip() for i in range(n))


def created(r):
    """建立成功：spec 5.1 寫 200、OpenAPI 寫 201，兩者不一致；狀態碼另有專門的測試，這裡只確認成功。"""
    assert r.status_code in (200, 201), r.text
    return r.json()
