"""必填文字欄位的共用檢查：去頭尾空白，空的欄位一次全部列出（VALIDATION_ERROR）。"""

from app.errors import DomainError


def required_texts(values: dict[str, str | None]) -> dict[str, str]:
    cleaned = {field: (value or "").strip() for field, value in values.items()}
    empty = sorted(field for field, value in cleaned.items() if not value)
    if empty:
        raise DomainError("VALIDATION_ERROR", details={"fields": empty})
    return cleaned
