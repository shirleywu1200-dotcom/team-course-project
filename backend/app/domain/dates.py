"""使用者輸入的日期字串轉值（收件 R2 與專案匯入共用）。純函式。"""

import re
from datetime import date, timedelta

from app.domain.due import check_date_range
from app.errors import DomainError

YEAR_ROLLOVER_DAYS = 180
_FULL = re.compile(r"^(\d{4})\s*[/／\-年]\s*(\d{1,2})\s*[/／\-月]\s*(\d{1,2})\s*日?$")
_MONTH_DAY = re.compile(r"^(\d{1,2})\s*[/／月]\s*(\d{1,2})\s*日?$")


def to_date(value, today: date) -> date | None:
    """`YYYY-MM-DD`、`YYYY/M/D`、`YYYY年M月D日`、`M/D`、`M月D日`。

    沒有年份時取今年，比今天早 180 天以上就算明年（Phase 6 SDD Q2）。轉不出來回 None。
    """
    if not isinstance(value, str):
        return None
    value = value.strip()
    m = _FULL.match(value)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    m = _MONTH_DAY.match(value)
    if not m:
        return None
    try:
        d = date(today.year, int(m[1]), int(m[2]))
    except ValueError:
        return None
    if d < today - timedelta(days=YEAR_ROLLOVER_DAYS):
        try:
            d = d.replace(year=d.year + 1)
        except ValueError:   # 2/29 跨到非閏年
            return None
    return d


def in_date_range(d: date | None, today: date) -> bool:
    """是否在日期調整允許的範圍內（今天前 365 天至後 730 天，due.check_date_range）。"""
    if d is None:
        return False
    try:
        check_date_range(d, today)
    except DomainError:
        return False
    return True
