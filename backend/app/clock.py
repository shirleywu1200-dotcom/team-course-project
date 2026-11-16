"""時鐘：所有「今天」與「現在」都從這裡取，測試時換成固定時鐘。

時區固定為 Asia/Taipei（spec 8.2）。
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")


class Clock:
    def now(self) -> datetime:
        return datetime.now(TZ)

    def today(self) -> date:
        return self.now().date()


class FixedClock(Clock):
    def __init__(self, at: datetime):
        self.at = at if at.tzinfo else at.replace(tzinfo=TZ)

    def now(self) -> datetime:
        return self.at

    def set(self, at: datetime) -> None:
        self.at = at if at.tzinfo else at.replace(tzinfo=TZ)


_current: Clock = Clock()


def get_clock() -> Clock:
    return _current


def set_clock(clock: Clock) -> None:
    global _current
    _current = clock
