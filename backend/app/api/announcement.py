"""公告信息 API：第一版占位。"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])


@router.get("/")
def list_announcements():
    return {"code": 0, "message": "ok", "data": []}
