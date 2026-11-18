"""領域例外與錯誤碼（spec 5.1、5.2）。

領域程式只丟 `DomainError(code, ...)`，HTTP 狀態由這張表決定。
新增錯誤碼需產品負責人核可（todo 5.7）。
"""

ERROR_STATUS: dict[str, int] = {
    "UNAUTHORIZED": 401,
    "NOT_FOUND": 404,
    "TASK_DONE": 409,
    "STALE_VERSION": 409,
    "CONFIRMATION_INVALID": 409,
    "CANDIDATE_NOT_OPEN": 409,
    "FEEDBACK_EXISTS": 409,
    "PAYLOAD_TOO_LARGE": 413,
    "VALIDATION_ERROR": 422,
    "NO_CHANGE": 422,
    "DATE_OUT_OF_RANGE": 422,
    "MARK_REQUIRED": 422,
    "INCLUDES_DONE_TASK": 422,
    "EMPTY_SELECTION": 422,
    "ACK_REQUIRED": 422,
    "ANNOTATION_NOT_ALLOWED": 422,
    "AI_UNAVAILABLE": 503,
    "INTERNAL_ERROR": 500,
}

DEFAULT_MESSAGES: dict[str, str] = {
    "UNAUTHORIZED": "缺少或錯誤的存取 token",
    "NOT_FOUND": "資源不存在",
    "TASK_DONE": "已完成的任務不可執行此操作",
    "STALE_VERSION": "資料已被更新，請重新載入後再操作",
    "CONFIRMATION_INVALID": "確認憑證已過期、已使用或任務已變動，請重新預覽",
    "CANDIDATE_NOT_OPEN": "候選已處理",
    "FEEDBACK_EXISTS": "這個任務已有完成回報",
    "PAYLOAD_TOO_LARGE": "內容超過大小上限",
    "VALIDATION_ERROR": "欄位缺漏或格式錯誤",
    "NO_CHANGE": "新值與目前值相同",
    "DATE_OUT_OF_RANGE": "日期超出允許範圍",
    "MARK_REQUIRED": "你的任務需要選擇時間管理註記，或選擇稍後註記",
    "INCLUDES_DONE_TASK": "清單含已完成任務",
    "EMPTY_SELECTION": "清單為空",
    "ACK_REQUIRED": "基準更正需要勾選聲明",
    "ANNOTATION_NOT_ALLOWED": "此事件不可補註記",
    "AI_UNAVAILABLE": "AI 暫時無法使用",
    "INTERNAL_ERROR": "伺服器內部錯誤",
}


class DomainError(Exception):
    def __init__(self, code: str, message: str | None = None, details: dict | None = None):
        if code not in ERROR_STATUS:
            raise ValueError(f"未登記的錯誤碼：{code}")
        self.code = code
        self.message = message or DEFAULT_MESSAGES[code]
        self.details = details or {}
        super().__init__(code)

    @property
    def status(self) -> int:
        return ERROR_STATUS[self.code]

    def to_body(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}
