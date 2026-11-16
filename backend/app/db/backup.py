"""資料庫備份（todo 1.6）：pg_dump custom 格式，保留最新 14 份。

指令由環境變數 G4_PG_DUMP_CMD 指定，pg_dump 的輸出寫到標準輸出，例如：
  pg_dump --format=custom --dbname=postgresql://…
  docker exec g4-pg pg_dump -U g4 --format=custom g4
用法：python -m app.db.backup <備份資料夾>
"""

import os
import shlex
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from app.clock import get_clock
from app.config import load_settings

KEEP = 14
PREFIX = "g4-"
SUFFIX = ".dump"


def default_command() -> list[str]:
    cmd = os.environ.get("G4_PG_DUMP_CMD")
    if cmd:
        return shlex.split(cmd)
    url = load_settings().database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return ["pg_dump", "--format=custom", f"--dbname={url}"]


def run_dump(target: Path, command: list[str]) -> None:
    with target.open("wb") as out:
        subprocess.run(command, stdout=out, check=True)  # noqa: S603 指令來自設定，不來自使用者輸入


def prune(folder: Path, keep: int = KEEP) -> list[Path]:
    """只留最新 keep 份；回傳被刪除的檔案。檔名含時間戳，依名稱排序即依時間排序。"""
    dumps = sorted(folder.glob(f"{PREFIX}*{SUFFIX}"))
    removed = dumps[:-keep] if len(dumps) > keep else []
    for p in removed:
        p.unlink()
    return removed


def backup(folder: Path, dump: Callable[[Path], None] | None = None, keep: int = KEEP) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{PREFIX}{get_clock().now():%Y%m%d-%H%M%S}{SUFFIX}"
    partial = target.with_suffix(".partial")
    (dump or (lambda p: run_dump(p, default_command())))(partial)
    partial.rename(target)
    prune(folder, keep)
    return target


if __name__ == "__main__":
    print(backup(Path(sys.argv[1] if len(sys.argv) > 1 else "backups")))
