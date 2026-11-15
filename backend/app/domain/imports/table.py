"""切表格與表頭規則對應（FR-IMP-01、02，todo 6.1、6.2）。純函式。"""

import csv
import io

from app.errors import DomainError

MAX_CHARS = 50_000
MAX_ROWS = 500
FIELDS = ("title", "owner", "start", "end")
REQUIRED = ("title", "end")

# 先找完全相同的表頭，再找包含關鍵字的；包含比對時先認負責人、日期，最後才認任務名稱，
# 避免「任務負責人」「Owner Name」被當成任務名稱。同一欄只對應一個欄位（SDD 2.2）
SUBSTRING_ORDER = ("owner", "start", "end", "title")
NOT_END = ("標準", "條件", "定義", "說明")   # 「完成標準」是完成條件，不是日期
KEYWORDS = {
    "title": ("任務", "名稱", "工作", "項目", "title", "task", "name"),
    "owner": ("負責", "owner", "assignee", "pic"),
    "start": ("開始", "起始", "start"),
    "end": ("結束", "期限", "截止", "到期", "完成", "due", "end", "deadline"),
}


def split_table(text: str) -> tuple[list[str], list[list[str]]]:
    """回傳 (表頭, 資料列)。首列為表頭；有 Tab 用 Tab 分隔，否則用逗號。全空白的列略過。"""
    if len(text) > MAX_CHARS:
        raise DomainError("PAYLOAD_TOO_LARGE", details={"max_chars": MAX_CHARS})
    first = next((ln for ln in text.splitlines() if ln.strip()), None)
    if first is None:
        raise DomainError("EMPTY_SELECTION", "沒有可解析的表格", {"fields": ["text"]})
    delimiter = "\t" if "\t" in first else ","
    # 整段交給 csv，引號內的換行（含空行）才不會被拆掉；全空白的列在解析後才略過
    rows = [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(text), delimiter=delimiter)]
    rows = [r for r in rows if any(r)]
    header, data = rows[0], rows[1:]
    if len(data) > MAX_ROWS:
        raise DomainError("PAYLOAD_TOO_LARGE", details={"max_rows": MAX_ROWS})
    return header, data


def map_by_rule(header: list[str]) -> dict[str, int | None]:
    keys = [name.replace(" ", "").lower() for name in header]
    mapping: dict[str, int | None] = dict.fromkeys(FIELDS)
    taken: set[int] = set()

    def claim(field: str, match) -> None:
        if mapping[field] is not None:
            return
        for i, key in enumerate(keys):
            if i not in taken and match(key):
                mapping[field] = i
                taken.add(i)
                return

    for field in FIELDS:
        claim(field, lambda key, f=field: key in KEYWORDS[f])
    for field in SUBSTRING_ORDER:
        claim(field, lambda key, f=field: any(k in key for k in KEYWORDS[f])
              and not (f == "end" and any(w in key for w in NOT_END)))
    return mapping


def is_complete(mapping: dict[str, int | None]) -> bool:
    return all(mapping.get(f) is not None for f in REQUIRED)


def valid_map(mapping, columns: int) -> dict[str, int | None] | None:
    """檢查 AI 或使用者給的對應：必填欄位為不重複的有效索引，選填可為 null。不合法回 None。"""
    if not isinstance(mapping, dict):
        return None
    out: dict[str, int | None] = {}
    for f in FIELDS:
        v = mapping.get(f)
        if v is None and f not in REQUIRED:
            out[f] = None
        elif type(v) is int and 0 <= v < columns:
            out[f] = v
        else:
            return None
    used = [v for v in out.values() if v is not None]
    return out if len(used) == len(set(used)) else None
