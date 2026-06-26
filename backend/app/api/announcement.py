"""公告信息 API - 从东方财富获取公告数据"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import akshare as ak

from app.db import get_db
from app.core.response import success_response
from app.models import Announcement, StockBasic

router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])


@router.get("/")
def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    ann_type: Optional[str] = None,
    is_risk: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """获取公告列表，支持搜索和过滤"""
    query = db.query(Announcement)

    # 关键词搜索
    if keyword:
        query = query.filter(Announcement.ann_title.contains(keyword))

    # 类型过滤
    if ann_type:
        query = query.filter(Announcement.ann_type == ann_type)

    # 风险标识过滤
    if is_risk is not None:
        risk_keywords = ['风险', '警示', '退市', '亏损', '减值', '违规']
        if is_risk:
            # 构建风险相关的过滤条件
            from sqlalchemy import or_
            risk_filter = or_(*[Announcement.ann_title.contains(kw) for kw in risk_keywords])
            query = query.filter(risk_filter)
        # else: show all (no risk filter)

    # 按时间倒序
    query = query.order_by(Announcement.publish_date.desc())

    # 获取总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    result = []
    for ann in items:
        result.append({
            "id": ann.id,
            "stock_code": ann.stock_code,
            "title": ann.ann_title,
            "ann_type": ann.ann_type,
            "disclosure_date": str(ann.publish_date) if ann.publish_date else None,
            "is_risk": any(kw in ann.ann_title for kw in ['风险', '警示', '退市']),
            "url": ann.pdf_url,
        })

    return success_response({
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/latest")
def get_latest_announcements(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """获取最近N天的公告（用于公告中心首页）"""
    from datetime import date
    start_date = date.today() - timedelta(days=days)

    items = (
        db.query(Announcement)
        .filter(Announcement.publish_date >= start_date)
        .order_by(Announcement.publish_date.desc())
        .limit(100)
        .all()
    )

    result = []
    for ann in items:
        result.append({
            "stock_code": ann.stock_code,
            "title": ann.ann_title,
            "date": str(ann.publish_date) if ann.publish_date else None,
            "ann_type": ann.ann_type,
            "url": ann.pdf_url,
        })

    return success_response(result)


@router.post("/fetch")
def fetch_announcements(
    stock_code: str = Query(..., description="股票代码"),
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """抓取指定股票的公告（通过akshare）"""
    stock_code = stock_code.strip()

    # 转换代码格式
    if stock_code.startswith("6"):
        symbol = f"sh{stock_code}"
    elif stock_code.startswith(("0", "3")):
        symbol = f"sz{stock_code}"
    else:
        symbol = f"sz{stock_code}"

    try:
        # 使用akshare获取公告
        df = ak.stock_zh_a_disclosure_report_cninfo(symbol=symbol)

        if df is None or df.empty:
            return success_response({"fetched": 0, "message": "暂无公告数据"})

        imported = 0
        for _, row in df.iterrows():
            try:
                # 解析公告日期
                publish_date = None
                if '公告日期' in row:
                    pd = row['公告日期']
                    if isinstance(pd, str):
                        publish_date = datetime.strptime(pd, "%Y-%m-%d").date()
                    elif hasattr(pd, 'date'):
                        publish_date = pd.date()

                # 检查是否已存在
                existing = (
                    db.query(Announcement)
                    .filter(
                        Announcement.stock_code == stock_code,
                        Announcement.ann_title == row.get('公告标题', ''),
                    )
                    .first()
                )

                if not existing:
                    ann = Announcement(
                        stock_code=stock_code,
                        ann_title=row.get('公告标题', ''),
                        ann_type=row.get('公告类型'),
                        publish_date=publish_date,
                        pdf_url=row.get('pdf路径') or row.get('巨潮链接'),
                        source='cninfo',
                    )
                    db.add(ann)
                    imported += 1

            except Exception as e:
                print(f"Error processing row: {e}")
                continue

        db.commit()
        return success_response({
            "fetched": imported,
            "total_in_db": db.query(Announcement).filter(Announcement.stock_code == stock_code).count(),
        })

    except Exception as e:
        return success_response({"fetched": 0, "error": str(e)})
