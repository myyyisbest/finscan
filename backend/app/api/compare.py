"""对标分析 API：多公司指标对比 + 行业中位值。"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Literal
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.auth import get_optional_user_id
from app.core.response import ok
from app.db import get_db
from app.models import FinIndicator, IndustryIndicatorMedian


router = APIRouter(prefix="/api/v1/compare", tags=["compare"])


@router.get("/indicators")
def compare_indicators(
    stock_codes: str = Query(description="逗号分隔股票代码，最多8个"),
    report_type: str = Query("Annual", description="报告类型 Q1/H1/Q3/Annual"),
    indicators: str = Query("roe,roa,net_margin,debt_to_assets,inventory_turnover,ar_turnover",
                            description="逗号分隔指标字段"),
    db: Session = Depends(get_db),
):
    """批量获取多家公司指定指标的对比数据。"""
    codes = [c.strip() for c in stock_codes.split(",") if c.strip()][:8]
    fields = [f.strip() for f in indicators.split(",") if f.strip()]

    rows = (
        db.query(FinIndicator)
        .filter(FinIndicator.stock_code.in_(codes),
                FinIndicator.report_type == report_type)
        .order_by(FinIndicator.report_date.desc())
        .all()
    )

    # 按股票取最新一期
    stock_map: dict[str, dict] = {}
    for r in rows:
        if r.stock_code not in stock_map:
            stock_map[r.stock_code] = {
                "report_date": r.report_date.isoformat() if r.report_date else None,
            }
            for f in fields:
                if hasattr(r, f):
                    v = getattr(r, f)
                    stock_map[r.stock_code][f] = str(v) if isinstance(v, Decimal) else v

    return ok({
        "report_type": report_type,
        "fields": fields,
        "data": stock_map,
    })


@router.get("/trend")
def compare_trend(
    stock_codes: str = Query(description="逗号分隔股票代码，最多4个"),
    field: str = Query("roe", description="指标字段"),
    periods: int = Query(8, description="最近期数"),
    db: Session = Depends(get_db),
):
    """多家公司同一指标的历史趋势对比。"""
    codes = [c.strip() for c in stock_codes.split(",") if c.strip()][:4]

    rows = (
        db.query(FinIndicator)
        .filter(FinIndicator.stock_code.in_(codes),
                getattr(FinIndicator, field, None) != None)
        .order_by(FinIndicator.report_date.desc())
        .limit(periods * len(codes))
        .all()
    )

    # 按股票分组
    trend_map: dict[str, list] = {c: [] for c in codes}
    for r in rows:
        v = getattr(r, field)
        if v is not None and len(trend_map.get(r.stock_code, [])) < periods:
            trend_map[r.stock_code].append({
                "report_date": r.report_date.isoformat() if r.report_date else None,
                "value": str(v) if isinstance(v, Decimal) else v,
            })

    # 反转（从旧到新）
    for k in trend_map:
        trend_map[k] = list(reversed(trend_map[k]))

    return ok({
        "field": field,
        "trends": trend_map,
    })


@router.get("/industry/median")
def industry_median(
    industry: str = Query(description="申万一级行业名称"),
    report_type: str = Query("Annual"),
    indicator: str = Query("gross_margin"),
    db: Session = Depends(get_db),
):
    """获取指定行业的指标中位值。"""
    row = (
        db.query(IndustryIndicatorMedian)
        .filter(IndustryIndicatorMedian.industry == industry,
                IndustryIndicatorMedian.report_type == report_type,
                IndustryIndicatorMedian.indicator_code == indicator)
        .order_by(IndustryIndicatorMedian.report_date.desc())
        .first()
    )
    if row:
        return ok({
            "industry": industry,
            "report_type": report_type,
            "indicator": indicator,
            "median_value": str(row.median_value) if row.median_value else None,
            "sample_count": row.sample_count,
        })
    return ok({"industry": industry, "median_value": None})


@router.post("/industry/calc-median")
def calc_industry_median(
    industry: str,
    report_type: str = "Annual",
    db: Session = Depends(get_db),
):
    """为指定行业计算指标中位值（定时任务调用）。"""
    indicators = ["roe", "roa", "net_margin", "debt_to_assets",
                  "current_ratio", "quick_ratio", "inventory_turnover",
                  "ar_turnover", "revenue_yoy", "net_profit_yoy",
                  "gross_margin", "total_asset_turnover"]
    from app.models import StockBasic
    codes = [s.stock_code for s in db.query(StockBasic).filter(StockBasic.industry == industry).all()]
    if not codes:
        return ok({"updated": 0})

    updated = 0
    for indicator in indicators:
        col = getattr(FinIndicator, indicator, None)
        if col is None:
            continue
        # 取该行业所有公司的最新一期
        from sqlalchemy import func, cast, Float
        result = (
            db.query(FinIndicator.report_date, col)
            .filter(FinIndicator.stock_code.in_(codes),
                    FinIndicator.report_type == report_type,
                    col != None)
            .group_by(FinIndicator.report_date)
            .all()
        )
        for report_date, val in result:
            if val is None:
                continue
            median_row = (
                db.query(IndustryIndicatorMedian)
                .filter(IndustryIndicatorMedian.industry == industry,
                        IndustryIndicatorMedian.report_date == report_date,
                        IndustryIndicatorMedian.indicator_code == indicator)
                .first()
            )
            if median_row is None:
                from datetime import datetime
                median_row = IndustryIndicatorMedian(
                    industry=industry, report_date=report_date,
                    indicator_code=indicator, sample_count=1,
                    calc_time=datetime.now())
                db.add(median_row)
            median_row.median_value = val
            updated += 1
    db.commit()
    return ok({"updated": updated})
