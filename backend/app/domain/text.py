"""必填文字欄位的共用檢查：去頭尾空白，空的欄位一次全部列出（VALIDATION_ERROR）。"""

from app.errors import DomainError


def blank_fields(values: dict[str, str | None]) -> list[str]:
    """去頭尾空白後為空的欄位，不丟錯；給需要和其他錯誤一起列出的呼叫者。"""
    return sorted(field for field, value in values.items() if not (value or "").strip())


def required_texts(values: dict[str, str | None]) -> dict[str, str]:
    empty = blank_fields(values)
    if empty:
        raise DomainError("VALIDATION_ERROR", details={"fields": empty})
    return {field: (value or "").strip() for field, value in values.items()}
