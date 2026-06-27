"""对标分析 API：基于 FinReport 表的多公司指标对比。"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.auth import get_optional_user_id
from app.core.response import ok
from app.db import get_db
from app.models import FinReport, StockBasic


router = APIRouter(prefix="/api/v1/compare", tags=["compare"])


@router.get("/report")
def compare_report(
    stock_codes: str = Query(description="逗号分隔股票代码，最多10个"),
    report_date: str = Query(description="报告期，格式 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """按具体报告期对比多家公司的核心财务指标（基于 FinReport 表）。"""
    codes = [c.strip() for c in stock_codes.split(",") if c.strip()][:10]

    rows = (
        db.query(FinReport)
        .filter(FinReport.stock_code.in_(codes),
                FinReport.report_date == report_date)
        .all()
    )

    # 代码 -> 名称映射
    basics = db.query(StockBasic).filter(StockBasic.stock_code.in_(codes)).all()
    name_map = {b.stock_code: b.stock_name for b in basics}

    def _f(v):
        return float(v) if v is not None else None

    data = []
    for r in rows:
        data.append({
            "stock_code": r.stock_code,
            "stock_name": name_map.get(r.stock_code, r.stock_code),
            "report_date": r.report_date.isoformat(),
            "report_name": r.report_name,
            "report_type": r.report_type,
            # 规模
            "total_revenue": _f(r.total_revenue),
            "net_profit_parent": _f(r.net_profit_parent),
            "total_assets": _f(r.total_assets),
            "total_equity": _f(r.total_equity),
            # 盈利能力
            "roe": _f(r.roe),
            "roa": _f(r.roa),
            "gross_margin": _f(r.gross_margin),
            "net_margin": _f(r.net_margin),
            # 偿债/资本结构
            "debt_ratio": _f(r.debt_ratio),
            "current_ratio": _f(r.current_ratio),
            "quick_ratio": _f(r.quick_ratio),
            # 成长
            "revenue_yoy": _f(r.revenue_yoy),
            "net_profit_yoy": _f(r.net_profit_yoy),
            # 运营效率
            "total_asset_turnover": _f(r.total_revenue) / _f(r.total_assets)
                if r.total_revenue and r.total_assets and float(r.total_assets) != 0 else None,
        })

    return ok({
        "report_date": report_date,
        "data": data,
    })


@router.get("/report-dates")
def compare_report_dates(
    stock_codes: str = Query(description="逗号分隔股票代码"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """获取多只股票的公共报告期列表（取交集，倒序）。"""
    codes = [c.strip() for c in stock_codes.split(",") if c.strip()]
    if not codes:
        return ok([])

    # 取第一只股票的报告期作为基准
    base_rows = (
        db.query(FinReport.report_date, FinReport.report_name, FinReport.report_type)
        .filter(FinReport.stock_code == codes[0])
        .order_by(FinReport.report_date.desc())
        .limit(limit)
        .all()
    )

    result = []
    for r in base_rows:
        # 检查所有股票是否都有该报告期
        count = (
            db.query(FinReport)
            .filter(FinReport.stock_code.in_(codes),
                    FinReport.report_date == r.report_date)
            .count()
        )
        if count == len(codes):
            result.append({
                "report_date": r.report_date.isoformat(),
                "report_name": r.report_name,
                "report_type": r.report_type,
            })

    return ok(result)
