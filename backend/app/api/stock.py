"""股票基础信息API：搜索、列表、基本信息。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.core.response import success_response, fail_response
from app.models import StockBasic, FinReport

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


@router.get("/search")
def search_stock(
    keyword: str = Query(..., min_length=1, description="搜索关键词（代码或名称）"),
    db: Session = Depends(get_db),
):
    """搜索股票：支持代码或名称模糊匹配。"""
    kw = keyword.strip()
    query = db.query(StockBasic)
    if kw.isdigit():
        results = query.filter(StockBasic.stock_code.like(f"%{kw}%")).limit(20).all()
    else:
        results = query.filter(
            (StockBasic.stock_name.like(f"%{kw}%")) |
            (StockBasic.stock_code.like(f"%{kw}%"))
        ).limit(20).all()
    return success_response([{
        "stock_code": s.stock_code,
        "stock_name": s.stock_name,
        "market": s.market,
        "secucode": s.secucode or s.secucode_format(),
        "industry": s.industry,
    } for s in results])


@router.get("/{code}")
def get_stock_info(code: str, db: Session = Depends(get_db)):
    """获取股票基本信息。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    stock = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
    if not stock:
        return fail_response("股票不存在", code=404)

    # 获取最新一期财务数据
    latest_report = (
        db.query(FinReport)
        .filter(FinReport.stock_code == code)
        .order_by(FinReport.report_date.desc())
        .first()
    )

    return success_response({
        "stock_code": stock.stock_code,
        "stock_name": stock.stock_name,
        "market": stock.market,
        "secucode": stock.secucode or stock.secucode_format(),
        "industry": stock.industry,
        "full_name": stock.full_name,
        "list_date": str(stock.list_date) if stock.list_date else None,
        "is_st": stock.is_st,
        "latest_report": {
            "report_date": str(latest_report.report_date) if latest_report else None,
            "report_name": latest_report.report_name if latest_report else None,
            "total_revenue": float(latest_report.total_revenue) if latest_report and latest_report.total_revenue else None,
            "net_profit_parent": float(latest_report.net_profit_parent) if latest_report and latest_report.net_profit_parent else None,
            "roe": float(latest_report.roe) if latest_report and latest_report.roe else None,
            "debt_ratio": float(latest_report.debt_ratio) if latest_report and latest_report.debt_ratio else None,
        } if latest_report else None,
    })


@router.get("/{code}/reports/dates")
def get_report_dates(
    code: str,
    report_type: Optional[str] = Query(None, description="Q1/H1/Q3/Annual"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """获取某股票的可用报告期列表（倒序）。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    query = db.query(FinReport).filter(FinReport.stock_code == code)
    if report_type:
        query = query.filter(FinReport.report_type == report_type)
    reports = query.order_by(FinReport.report_date.desc()).limit(limit).all()
    return success_response([{
        "report_date": str(r.report_date),
        "report_name": r.report_name,
        "report_type": r.report_type,
        "notice_date": str(r.notice_date) if r.notice_date else None,
    } for r in reports])
