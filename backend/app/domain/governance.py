"""資料控制：原文到期清除、全部清除、匯出（todo 8.5～8.7、FR-GOV-01～03；Phase 8 SDD 第 4～6 節）。

只清 `sources.excerpt`、可能快取原句的 `idempotency_keys`，以及可能含原文的 `ai_runs.raw_output`（PR #20 B2）；
events、candidates、tasks 保留（spec 6.7）。
"""

from datetime import date, datetime, timedelta

from sqlalchemy import Connection

from app.clock import get_clock
from app.config import IDEMPOTENCY_TTL
from app.db.repo import ai_runs_repo, governance_repo, settings_repo, sources_repo
from app.errors import DomainError


def purge_expired(conn: Connection) -> int:
    """到期原文清除（冪等）。順便刪掉超過保存期限的冪等快取（DA-23）。

    有原文被清掉時，快取全部刪除：快取的回應本文可能含剛清掉的原句，留著就清不乾淨。
    """
    now = get_clock().now()
    purged = sources_repo.purge_expired(conn, now)
    retention = timedelta(days=settings_repo.get(conn)["retention_days"])
    ai_runs_repo.clear_raw_output_before(conn, now - retention)
    if purged:
        governance_repo.delete_all_idempotency(conn)
    else:
        governance_repo.delete_idempotency_before(conn, now - IDEMPOTENCY_TTL)
    return purged


def purge_all(conn: Connection, confirm: bool) -> int:
    if confirm is not True:
        raise DomainError("VALIDATION_ERROR", "需要 confirm=true 才會刪除所有來源原文",
                          details={"fields": ["confirm"]})
    governance_repo.delete_all_idempotency(conn)
    ai_runs_repo.clear_all_raw_output(conn)
    return sources_repo.purge_all(conn, get_clock().now())


def _jsonable(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def export(conn: Connection) -> dict:
    """全部資料表的一致快照（AC-54）。呼叫端須讓這是交易內第一個操作。"""
    governance_repo.begin_snapshot(conn)
    tables = {t: [{k: _jsonable(v) for k, v in row.items()} for row in governance_repo.dump_table(conn, t)]
              for t in governance_repo.table_names(conn)}
    return {"exported_at": get_clock().now().isoformat(), "schema_version": governance_repo.schema_version(conn),
            "counts": {t: len(rows) for t, rows in tables.items()}, "tables": tables}
