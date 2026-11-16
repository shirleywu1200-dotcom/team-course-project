"""共用的資料列寫入工具。

欄位名稱來自程式內的白名單，值一律走參數綁定（CLAUDE.md 資安 6）。
"""

import json

from sqlalchemy import Connection, text

JSONB_COLUMNS = {"extra", "payload", "result", "proposed", "suggest", "detail", "response",
                 "levels", "interview", "goal_types_enabled", "ai_items"}


def _param(col: str, value):
    if col in JSONB_COLUMNS and value is not None and not isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return value


def _placeholder(col: str) -> str:
    return f"CAST(:{col} AS jsonb)" if col in JSONB_COLUMNS else f":{col}"


def insert_row(conn: Connection, table: str, columns: set[str], fields: dict) -> dict:
    unknown = set(fields) - columns
    if unknown:
        raise ValueError(f"{table} 沒有欄位：{sorted(unknown)}")
    cols = sorted(fields)
    sql = (f"INSERT INTO {table} ({', '.join(cols)}) "  # noqa: S608 欄位名稱來自白名單
           f"VALUES ({', '.join(_placeholder(c) for c in cols)}) RETURNING *")
    row = conn.execute(text(sql), {c: _param(c, fields[c]) for c in cols}).mappings().one()
    return dict(row)


def update_row(conn: Connection, table: str, columns: set[str], row_id, fields: dict,
               extra_set: str = "") -> dict:
    unknown = set(fields) - columns
    if unknown:
        raise ValueError(f"{table} 沒有欄位：{sorted(unknown)}")
    sets = [f"{c} = {_placeholder(c)}" for c in sorted(fields)]
    if extra_set:
        sets.append(extra_set)
    sql = f"UPDATE {table} SET {', '.join(sets)} WHERE id = :_id RETURNING *"  # noqa: S608 同上
    params = {c: _param(c, fields[c]) for c in fields} | {"_id": row_id}
    return dict(conn.execute(text(sql), params).mappings().one())
