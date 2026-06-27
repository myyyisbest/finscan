"""公告信息 API - 优先从数据库读取，没有则实时获取入库"""
import logging
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd

from app.db import get_db
from app.core.response import success_response
from app.core.auth import get_current_user
from app.models import Watchlist, Announcement

router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])


@router.get("/")
def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    ann_type: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取公告列表，只显示当前用户自选股票相关的公告。
    
    优先从数据库读取，如果数据库中数据不足，则实时获取并入库。
    """
    # 获取用户自选股票代码列表
    watchlist_items = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id
    ).all()
    watchlist_codes = [item.stock_code for item in watchlist_items]

    if not watchlist_codes:
        return success_response({
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        })

    # 计算日期范围
    cutoff_date = (datetime.now() - timedelta(days=days)).date()

    # 先从数据库查询
    query = db.query(Announcement).filter(
        Announcement.stock_code.in_(watchlist_codes),
        Announcement.publish_date >= cutoff_date,
    )

    if ann_type:
        query = query.filter(Announcement.ann_type == ann_type)

    if keyword:
        query = query.filter(Announcement.ann_title.like(f"%{keyword}%"))

    total = query.count()

    # 如果数据库有数据，直接返回
    if total > 0:
        items = (
            query.order_by(Announcement.publish_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        result = []
        for ann in items:
            result.append({
                "stock_code": ann.stock_code,
                "stock_name": _get_stock_name(db, ann.stock_code),
                "title": ann.ann_title,
                "ann_type": ann.ann_type or "",
                "disclosure_date": str(ann.publish_date),
                "url": ann.pdf_url or "",
            })
        return success_response({
            "items": result,
            "total": total,
            "page": page,
            "page_size": page_size,
        })

    # 数据库没有数据，实时获取并入库
    try:
        import akshare as ak
        all_data = []
        for code in watchlist_codes:
            try:
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
                df = ak.stock_individual_notice_report(
                    security=code,
                    symbol="全部",
                    begin_date=start_date,
                    end_date=end_date,
                )
                if df is not None and len(df) > 0:
                    all_data.append(df)
                    # 边获取边入库
                    _save_announcements(db, code, df)
            except Exception as e:
                logging.warning(f"获取 {code} 公告失败: {e}")
                continue

        if not all_data:
            return success_response({
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            })

        # 重新从数据库查询（因为刚入库了）
        query = db.query(Announcement).filter(
            Announcement.stock_code.in_(watchlist_codes),
            Announcement.publish_date >= cutoff_date,
        )
        if ann_type:
            query = query.filter(Announcement.ann_type == ann_type)
        if keyword:
            query = query.filter(Announcement.ann_title.like(f"%{keyword}%"))

        total = query.count()
        items = (
            query.order_by(Announcement.publish_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        result = []
        for ann in items:
            result.append({
                "stock_code": ann.stock_code,
                "stock_name": _get_stock_name(db, ann.stock_code),
                "title": ann.ann_title,
                "ann_type": ann.ann_type or "",
                "disclosure_date": str(ann.publish_date),
                "url": ann.pdf_url or "",
            })
        return success_response({
            "items": result,
            "total": total,
            "page": page,
            "page_size": page_size,
        })
    except Exception as e:
        logging.error(f"获取公告列表失败: {e}")
        return success_response({
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        })


def _get_stock_name(db: Session, code: str) -> str:
    """从Watchlist获取股票名称（避免额外查询StockBasic）。"""
    from app.models import StockBasic
    stock = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
    return stock.stock_name if stock else code


def _save_announcements(db: Session, code: str, df):
    """将公告数据保存到数据库（去重）。"""
    from datetime import date as date_type
    for _, row in df.iterrows():
        title = str(row.get("公告标题", "")).strip()
        pub_date_str = str(row.get("公告日期", ""))[:10]
        if not title or not pub_date_str:
            continue
        try:
            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        existing = db.query(Announcement).filter(
            Announcement.stock_code == code,
            Announcement.ann_title == title,
            Announcement.publish_date == pub_date,
        ).first()
        if existing:
            continue

        ann = Announcement(
            stock_code=code,
            ann_title=title,
            ann_type=str(row.get("公告类型", "")) or None,
            publish_date=pub_date,
            pdf_url=str(row.get("网址", "")) or None,
            source="eastmoney",
        )
        db.add(ann)
    db.commit()


@router.get("/types")
def get_announcement_types():
    """获取公告类型列表"""
    return success_response([
        "全部",
        "定期报告",
        "业绩预告",
        "重大事项",
        "风险提示",
        "分配方案实施",
        "股份质押、冻结",
        "回购预案",
        "高管人员任职变动",
        "法律意见书",
        "监事会决议公告",
        "股东会决议公告",
    ])
