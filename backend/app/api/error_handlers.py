"""把例外轉成統一錯誤格式 {error:{code,message,details}}（spec 5.1）。

錯誤回應只放欄位名稱與 ID，不回傳使用者送來的內容（CLAUDE.md 資安 3）。
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import DomainError


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

    # 未預期的例外由 app.api.middleware.UnhandledErrorMiddleware 處理：
    # 用 exception_handler(Exception) 的話，Starlette 會在回應後把例外再拋出，
    # uvicorn 會把含錯誤訊息的完整 traceback 寫進 log。
