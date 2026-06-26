"""股票基础信息API：搜索、列表、基本信息、公司简介。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.db import get_db
from app.core.response import success_response, fail_response
from app.models import StockBasic, FinReport

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])

log = logging.getLogger(__name__)


def _detect_market(code: str) -> str:
    """根据代码判断市场"""
    code = code.strip()
    if code.startswith("6"):
        return "SH"
    elif code.startswith("0") or code.startswith("3"):
        return "SZ"
    elif code.startswith("4") or code.startswith("8"):
        return "BJ"
    return "SZ"


def _get_xq_symbol(code: str) -> str:
    """获取雪球格式的symbol（如SH601127）"""
    return f"{_detect_market(code)}{code}"


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


@router.get("/{code}/profile")
def get_stock_profile(code: str, db: Session = Depends(get_db)):
    """获取公司简介：调用akshare的stock_individual_basic_info_xq接口。

    返回字段：org_id/cnsp_id/org_name_cn/org_name_en/org_short_name_cn/org_short_name_en/
    currency/listed_date/raised_capital/established_date/actual_controller/actual_controller_amount/
    classi_name/pre_name/main_business/business_scope/office_address/org_website/org_telephone/
    org_email/reg_address/reg_capital/enterprise_type/legal_rep/secretary/province/city/area/
    employees_number/main_holders_count/main_business_scope/description/...
    """
    code_clean = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    xq_symbol = _get_xq_symbol(code_clean)

    # 先从数据库获取基础信息（保证一定有数据）
    stock = db.query(StockBasic).filter(StockBasic.stock_code == code_clean).first()
    basic_info = {
        "stock_code": stock.stock_code if stock else code_clean,
        "stock_name": stock.stock_name if stock else None,
        "full_name": stock.full_name if stock else None,
        "industry": stock.industry if stock else None,
        "market": stock.market if stock else _detect_market(code_clean),
        "list_date": str(stock.list_date) if stock and stock.list_date else None,
    }

    # 调用akshare获取公司简介
    profile_data = None
    error_msg = None
    try:
        import akshare as ak
        df = ak.stock_individual_basic_info_xq(symbol=xq_symbol)
        if df is not None and len(df) > 0:
            # 转换为 {字段: 值} 的字典
            profile_data = dict(zip(df.iloc[:, 0].tolist(), df.iloc[:, 1].tolist()))
    except Exception as e:
        error_msg = str(e)
        log.warning("akshare stock_individual_basic_info_xq 失败: %s", e)

    if not profile_data:
        return success_response({
            "basic": basic_info,
            "profile": None,
            "error": error_msg or "akshare接口暂不可用",
        })

    return success_response({
        "basic": basic_info,
        "profile": profile_data,
        "error": None,
    })
