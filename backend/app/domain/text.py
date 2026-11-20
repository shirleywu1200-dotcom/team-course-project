"""文字欄位的共用檢查：必填欄位（去頭尾空白，空的一次全部列出）與人工版文字（週報、目標回報）。"""

from app.errors import DomainError


def blank_fields(values: dict[str, str | None]) -> list[str]:
    """去頭尾空白後為空的欄位，不丟錯；給需要和其他錯誤一起列出的呼叫者。"""
    return sorted(field for field, value in values.items() if not (value or "").strip())


def required_texts(values: dict[str, str | None]) -> dict[str, str]:
    empty = blank_fields(values)
    if empty:
        raise DomainError("VALIDATION_ERROR", details={"fields": empty})
    return {field: (value or "").strip() for field, value in values.items()}


def check_manual_text(manual_text: str | None, max_chars: int) -> None:
    """人工版（週報 5.14、目標回報 5.13）：超過上限 413、含 NUL 422；錯誤只帶欄名與上限，不帶內容。"""
    if manual_text is None:
        return
    if len(manual_text) > max_chars:
        raise DomainError("PAYLOAD_TOO_LARGE", details={"max_chars": max_chars})
    if "\x00" in manual_text:   # PostgreSQL 的文字欄位不收 NUL
        raise DomainError("VALIDATION_ERROR", "manual_text 含有不能使用的字元", {"fields": ["manual_text"]})
