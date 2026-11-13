"""把例外轉成統一錯誤格式 {error:{code,message,details}}（spec 5.1）。

錯誤回應只放欄位名稱與 ID，不回傳使用者送來的內容（CLAUDE.md 資安 3）。
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import DomainError

log = logging.getLogger("g4")


def _json(err: DomainError) -> JSONResponse:
    return JSONResponse(err.to_body(), status_code=err.status)


def install(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError):
        return _json(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        fields = sorted({".".join(str(p) for p in e["loc"] if p != "body") for e in exc.errors()})
        return _json(DomainError("VALIDATION_ERROR", details={"fields": fields}))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return _json(DomainError("NOT_FOUND"))
        if exc.status_code == 405:
            return _json(DomainError("NOT_FOUND", "此路徑不支援這個方法"))
        return JSONResponse({"error": {"code": "HTTP_ERROR", "message": str(exc.detail), "details": {}}},
                            status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception):
        log.error("unhandled error: %s", type(exc).__name__)   # 只記類型，不記內容
        return _json(DomainError("INTERNAL_ERROR"))
