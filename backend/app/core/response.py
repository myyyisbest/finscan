"""统一响应封装。

所有接口统一返回:
{
  "code": 0,
  "message": "success",
  "data": {...},
  "timestamp": 1718888888
}
错误码: 0成功 / 1001参数错误 / 2001数据不存在 / 3001权限错误 / 5000服务器错误
"""
import time
import math
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None
    timestamp: int = 0

    def __init__(self, **data):  # type: ignore[no-untyped-def]
        data.setdefault("timestamp", int(time.time()))
        super().__init__(**data)


def ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data, "timestamp": int(time.time())}


success_response = ok


def fail_response(message: str = "error", code: int = 5000, data: Any = None) -> dict:
    """fail_response(message, code=xxx) 兼容新API调用方式。"""
    return {"code": code, "message": message, "data": data, "timestamp": int(time.time())}


def fail(code: int = 5000, message: str = "error", data: Any = None) -> dict:
    """fail(code=xxx, message=xxx) 旧API兼容。"""
    return {"code": code, "message": message, "data": data, "timestamp": int(time.time())}


class PageData(BaseModel, Generic[T]):
    """分页数据载荷"""
    items: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0

    @classmethod
    def build(cls, items: list, total: int, page: int, page_size: int) -> "PageData":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        )
