"""公告信息 API：公告列表 + 详情 + 同步（附注已并入）。"""
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_optional_user_id
from app.core.response import ok
from app.db import get_db
from app.models import Announcement, NoteMainBusiness, CollectTaskLog


router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])


# ---- 查询 ----

@router.get("/")
def list_announcements(
    stock_code: str | None = None,
    ann_type: str | None = None,
    is_risk: bool | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Announcement)
    if stock_code:
        q = q.filter(Announcement.stock_code == stock_code)
    if ann_type:
        q = q.filter(Announcement.ann_type == ann_type)
    if is_risk is not None:
        q = q.filter(Announcement.is_risk == is_risk)
    if keyword:
        q = q.filter(Announcement.ann_title.like(f"%{keyword}%"))
    total = q.count()
    rows = (
        q.order_by(Announcement.publish_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": r.id,
            "stock_code": r.stock_code,
            "ann_title": r.ann_title,
            "ann_type": r.ann_type,
            "publish_date": r.publish_date.isoformat() if r.publish_date else None,
            "is_risk": r.is_risk,
            "pdf_url": r.pdf_url,
            "content_summary": r.content_summary,
        }
        for r in rows
    ]
    from app.core.response import PageData
    return ok(PageData.build(items, total, page, page_size))


@router.get("/{ann_id}")
def get_announcement(ann_id: int, db: Session = Depends(get_db)):
    r = db.get(Announcement, ann_id)
    if r is None:
        return {"code": 2001, "message": "公告不存在"}
    return ok({
        "id": r.id, "stock_code": r.stock_code, "ann_title": r.ann_title,
        "ann_type": r.ann_type,
        "publish_date": r.publish_date.isoformat() if r.publish_date else None,
        "pdf_url": r.pdf_url, "content_summary": r.content_summary,
        "is_risk": r.is_risk, "source": r.source,
    })


# ---- 主营附注 API ----

@router.get("/notes/main-business")
def list_main_business(
    stock_code: str,
    report_date: str | None = None,
    biz_type: str | None = Query(None, description="产品/行业/地区"),
    db: Session = Depends(get_db),
):
    q = db.query(NoteMainBusiness).filter(NoteMainBusiness.stock_code == stock_code)
    if report_date:
        try:
            d = date.fromisoformat(report_date[:10])
            q = q.filter(NoteMainBusiness.report_date == d)
        except ValueError:
            pass
    if biz_type:
        q = q.filter(NoteMainBusiness.biz_type == biz_type)
    q = q.order_by(NoteMainBusiness.report_date.desc())
    rows = q.all()
    return ok([
        {
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "biz_type": r.biz_type,
            "biz_name": r.biz_name,
            "revenue": str(r.revenue) if r.revenue else None,
            "cost": str(r.cost) if r.cost else None,
            "gross_profit": str(r.gross_profit) if r.gross_profit else None,
            "gross_margin": str(r.gross_margin) if r.gross_margin else None,
            "revenue_ratio": str(r.revenue_ratio) if r.revenue_ratio else None,
        }
        for r in rows
    ])
