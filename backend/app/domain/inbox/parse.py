"""把貼上的文字拆成訊息（Phase 7 SDD 2.1：寬鬆解析）。純函式，不碰資料庫。

每行依序試：A 時間＋發言者＋內容 → B 發言者：內容 → C 接到上一則訊息。
認不出、前面又沒有訊息可接的行，回報行號，讓使用者修正後重貼。
"""

import hashlib
import re
from dataclasses import dataclass, field, replace

MAX_SPEAKER_LEN = 20
_SPACES = " \t　"

_TIME = re.compile(r"^[\[［【(（]?\s*(上午|下午)?\s*(\d{1,2})[:：](\d{2})\s*[\]］】)）]?")
_SPEAKER_COLON = re.compile(r"^([^:：\t]{1," + str(MAX_SPEAKER_LEN) + r"}?)\s*[:：]\s*(\S.*)$")
_DATE_HEADER = re.compile(
    r"^(\d{4})\s*[/.\-年]\s*(\d{1,2})\s*[/.\-月]\s*(\d{1,2})\s*日?\s*"
    r"([（(]?\s*(星期|週|周)?\s*[一二三四五六日天]\s*[)）]?)?$"
)


@dataclass(frozen=True)
class Message:
    line_no: int
    spoken_at: str | None
    speaker: str
    text: str
    date: str | None = None   # 前面最近一個日期標頭（YYYY-MM-DD）；沒有標頭時為 None

    @property
    def hash(self) -> str:
        """去重用：時間＋發言者＋內容（FR-INB-04）；有日期標頭時日期也併入（PR #20 B3）。"""
        key = f"{self.spoken_at or ''}\n{self.speaker}\n{self.text}"
        if self.date:
            key = f"{self.date}\n{key}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass
class ParseResult:
    messages: list[Message] = field(default_factory=list)
    unparsed_lines: list[int] = field(default_factory=list)
    line_count: int = 0   # 非空白行數，用來判斷同步或背景（FR-INB-05）


def _time_of(m: re.Match) -> str | None:
    ampm, hour, minute = m[1], int(m[2]), int(m[3])
    if ampm == "下午" and hour < 12:
        hour += 12
    elif ampm == "上午" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _split_speaker(rest: str, allow_space: bool) -> tuple[str, str] | None:
    """從「發言者＋分隔＋內容」拆出兩段。分隔可以是冒號、Tab，有時間時也可以是空白。"""
    tab = rest.find("\t")
    colon = _SPEAKER_COLON.match(rest)
    if colon and colon[2].startswith("//"):   # 網址（https://…）不是「發言者：內容」
        colon = None
    if colon and (tab == -1 or colon.end(1) < tab):
        speaker, text = colon[1], colon[2]
    elif tab > 0:
        speaker, text = rest[:tab], rest[tab:]
    elif allow_space:
        parts = re.split(r"[ 　]+", rest, maxsplit=1)
        if len(parts) < 2:
            return None
        speaker, text = parts
    else:
        return None
    speaker, text = speaker.strip(_SPACES), text.strip(_SPACES)
    if not speaker or not text or len(speaker) > MAX_SPEAKER_LEN:
        return None
    return speaker, text


def parse_line(line: str) -> tuple[str | None, str, str] | None:
    """回傳 (spoken_at, speaker, text)；認不出時回 None。"""
    m = _TIME.match(line)
    if m:   # 行首像時間，就只試樣式 A；時間無效時不退回樣式 B，免得把「25:99」拆成發言者「25」
        spoken_at = _time_of(m)
        pair = _split_speaker(line[m.end():].strip(_SPACES), allow_space=True) if spoken_at else None
        return (spoken_at, *pair) if pair else None
    pair = _split_speaker(line, allow_space=False)
    return (None, *pair) if pair else None


def parse_text(text: str) -> ParseResult:
    result = ParseResult()
    current_date = None
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        result.line_count += 1
        header = _DATE_HEADER.match(line)
        if header:
            current_date = f"{header[1]}-{int(header[2]):02d}-{int(header[3]):02d}"
            continue
        parsed = parse_line(line)
        if parsed:
            result.messages.append(Message(line_no, *parsed, date=current_date))
        elif result.messages:
            last = result.messages[-1]
            result.messages[-1] = replace(last, text=f"{last.text}\n{line}")
        else:
            result.unparsed_lines.append(line_no)
    return result
