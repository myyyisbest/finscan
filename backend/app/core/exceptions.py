"""业务异常 + 全局异常处理。

统一把异常转成 Response JSON，避免裸露 500。
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .response import fail


class BizException(Exception):
    """业务异常，携带错误码与消息"""
    def __init__(self, code: int = 5000, message: str = "服务器内部错误"):
        self.code = code
        self.message = message
        super().__init__(message)


class NotFoundError(BizException):
    def __init__(self, message: str = "数据不存在"):
        super().__init__(code=2001, message=message)


class AuthError(BizException):
    def __init__(self, message: str = "未授权或登录已过期"):
        super().__init__(code=3001, message=message)


class ParamError(BizException):
    def __init__(self, message: str = "参数错误"):
        super().__init__(code=1001, message=message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizException)
    async def _biz_handler(_: Request, exc: BizException):
        return JSONResponse(status_code=200, content=fail(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=200, content=fail(1001, f"参数校验失败: {exc.errors()}"))

    @app.exception_handler(Exception)
    async def _global_handler(_: Request, exc: Exception):
        return JSONResponse(status_code=200, content=fail(5000, f"服务器内部错误: {exc}"))
