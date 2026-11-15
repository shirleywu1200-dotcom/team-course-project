"""單列解析與診斷（FR-IMP-03、04，todo 6.3、6.4）。純函式；preview 與 commit 共用同一套規則。"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.domain.dates import in_date_range, to_date
from app.domain.events import OWNER_ME

START_BEFORE_END_DAYS = 3

_MESSAGES = {
    "TITLE_MISSING": "缺任務名稱",
    "END_MISSING": "缺結束日期或無法解析",
    "END_BEFORE_START": "結束日期早於開始日期",
    "DATE_OUT_OF_RANGE": "結束日期超出允許範圍",
    "OWNER_MISSING": "缺負責人，匯入時預設為「我」",
    "START_MISSING": "缺開始日期，以結束前 3 天代入",
    "DUPLICATE_TITLE": "名稱與前面的列重複",
}
_ERRORS = {"TITLE_MISSING", "END_MISSING", "END_BEFORE_START", "DATE_OUT_OF_RANGE"}


@dataclass
class Row:
    index: int
    title: str
    owner: str
    start: date | None
    end: date | None
    codes: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> bool:
        return any(c in _ERRORS for c in self.codes)

    def out(self) -> dict:
        return {"index": self.index, "title": self.title, "owner": self.owner, "start": self.start,
                "end": self.end, "blocking": self.blocking,
                "issues": [{"level": "error" if c in _ERRORS else "warn", "code": c, "message": _MESSAGES[c]}
                           for c in self.codes]}


def diagnose(index: int, title: str, owner: str, start_raw, end_raw, today: date, seen_titles: set[str]) -> Row:
    """seen_titles 由呼叫端依列序傳入並累積，用來判斷「與前列重複」。"""
    title, owner = (title or "").strip(), (owner or "").strip()
    end, start = to_date(end_raw, today), to_date(start_raw, today)
    codes = []
    if not title:
        codes.append("TITLE_MISSING")
    if end is None:
        codes.append("END_MISSING")
    elif not in_date_range(end, today):
        codes.append("DATE_OUT_OF_RANGE")
    if not owner:
        codes.append("OWNER_MISSING")
        owner = OWNER_ME
    if start is None:
        codes.append("START_MISSING")
        start = end - timedelta(days=START_BEFORE_END_DAYS) if end else None
    elif end is not None and end < start:
        codes.append("END_BEFORE_START")
    if title and title in seen_titles:
        codes.append("DUPLICATE_TITLE")
    seen_titles.add(title)
    return Row(index, title, owner, start, end, codes)
