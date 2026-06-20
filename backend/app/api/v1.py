"""API v1 Router —— 公司检索 + 财务报表/指标查询。

统一前缀: /api/v1
所有接口返回: {code, message, data, timestamp}
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.response import ok, PageData
from app.core.exceptions import NotFoundError
from app.db import get_db
from app.models import (
    StockBasic, BalanceSheet, IncomeStatement, CashFlow, FinIndicator,
)


router = APIRouter(prefix="/api/v1", tags=["v1"])


# ========== 股票检索 ==========

@router.get("/stocks/search")
def search_stocks(
    keyword: str = Query(default="", description="股票代码/名称模糊检索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(StockBasic)
    keyword = keyword.strip()
    if keyword:
        q = q.filter(
            (StockBasic.stock_code.like(f"%{keyword}%"))
            | (StockBasic.stock_name.like(f"%{keyword}%"))
        )
    total = q.count()
    rows = (
        q.order_by(StockBasic.stock_code)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "stock_code": r.stock_code,
            "stock_name": r.stock_name,
            "industry": r.industry,
            "market": r.market,
            "is_st": r.is_st,
        }
        for r in rows
    ]
    return ok(PageData.build(items, total, page, page_size))


@router.get("/stocks/{stock_code}/basic")
def get_stock_basic(stock_code: str, db: Session = Depends(get_db)):
    r = db.query(StockBasic).filter(StockBasic.stock_code == stock_code).first()
    if r is None:
        raise NotFoundError(f"未找到股票: {stock_code}")
    return ok({
        "stock_code": r.stock_code,
        "stock_name": r.stock_name,
        "full_name": r.full_name,
        "industry": r.industry,
        "market": r.market,
        "is_st": r.is_st,
        "update_time": r.update_time.isoformat() if r.update_time else None,
    })


# ========== 财务报表 ==========

def _paginate_query(q, page: int, page_size: int, transform):
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    items = [transform(r) for r in rows]
    return PageData.build(items, total, page, page_size)


@router.get("/stocks/{stock_code}/balance-sheet")
def get_balance_sheet(
    stock_code: str,
    report_type: Optional[str] = Query(None, description="Q1/H1/Q3/Annual，不填=全部"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(BalanceSheet).filter(BalanceSheet.stock_code == stock_code)
    if report_type:
        q = q.filter(BalanceSheet.report_type == report_type)
    q = q.order_by(BalanceSheet.report_date.desc())

    def to_item(r):
        return {
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "report_type": r.report_type,
            "total_assets": str(r.total_assets) if r.total_assets else None,
            "total_current_assets": str(r.total_current_assets) if r.total_current_assets else None,
            "monetary_funds": str(r.monetary_funds) if r.monetary_funds else None,
            "accounts_receivable": str(r.accounts_receivable) if r.accounts_receivable else None,
            "inventory": str(r.inventory) if r.inventory else None,
            "fixed_assets": str(r.fixed_assets) if r.fixed_assets else None,
            "construction_in_progress": str(r.construction_in_progress) if r.construction_in_progress else None,
            "intangible_assets": str(r.intangible_assets) if r.intangible_assets else None,
            "goodwill": str(r.goodwill) if r.goodwill else None,
            "long_deferred_expenses": str(r.long_deferred_expenses) if r.long_deferred_expenses else None,
            "total_liabilities": str(r.total_liabilities) if r.total_liabilities else None,
            "total_current_liabilities": str(r.total_current_liabilities) if r.total_current_liabilities else None,
            "short_term_borrowings": str(r.short_term_borrowings) if r.short_term_borrowings else None,
            "accounts_payable": str(r.accounts_payable) if r.accounts_payable else None,
            "long_term_borrowings": str(r.long_term_borrowings) if r.long_term_borrowings else None,
            "bonds_payable": str(r.bonds_payable) if r.bonds_payable else None,
            "total_equity": str(r.total_equity) if r.total_equity else None,
            "share_capital": str(r.share_capital) if r.share_capital else None,
            "capital_reserve": str(r.capital_reserve) if r.capital_reserve else None,
            "retained_profits": str(r.retained_profits) if r.retained_profits else None,
            "other_receivables": str(r.other_receivables) if r.other_receivables else None,
        }
    return ok(_paginate_query(q, page, page_size, to_item))


@router.get("/stocks/{stock_code}/income-statement")
def get_income_statement(
    stock_code: str,
    report_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(IncomeStatement).filter(IncomeStatement.stock_code == stock_code)
    if report_type:
        q = q.filter(IncomeStatement.report_type == report_type)
    q = q.order_by(IncomeStatement.report_date.desc())

    def to_item(r):
        return {
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "report_type": r.report_type,
            "total_revenue": str(r.total_revenue) if r.total_revenue else None,
            "operating_cost": str(r.operating_cost) if r.operating_cost else None,
            "gross_profit": str(r.gross_profit) if r.gross_profit else None,
            "gross_margin": str(r.gross_margin) if r.gross_margin else None,
            "selling_expenses": str(r.selling_expenses) if r.selling_expenses else None,
            "admin_expenses": str(r.admin_expenses) if r.admin_expenses else None,
            "rd_expenses": str(r.rd_expenses) if r.rd_expenses else None,
            "financial_expenses": str(r.financial_expenses) if r.financial_expenses else None,
            "operating_profit": str(r.operating_profit) if r.operating_profit else None,
            "total_profit": str(r.total_profit) if r.total_profit else None,
            "net_profit": str(r.net_profit) if r.net_profit else None,
            "net_profit_parent": str(r.net_profit_parent) if r.net_profit_parent else None,
            "net_profit_deduct": str(r.net_profit_deduct) if r.net_profit_deduct else None,
            "asset_impairment_loss": str(r.asset_impairment_loss) if r.asset_impairment_loss else None,
            "other_income": str(r.other_income) if r.other_income else None,
            "investment_income": str(r.investment_income) if r.investment_income else None,
        }
    return ok(_paginate_query(q, page, page_size, to_item))


@router.get("/stocks/{stock_code}/cash-flow")
def get_cash_flow(
    stock_code: str,
    report_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(CashFlow).filter(CashFlow.stock_code == stock_code)
    if report_type:
        q = q.filter(CashFlow.report_type == report_type)
    q = q.order_by(CashFlow.report_date.desc())

    def to_item(r):
        return {
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "report_type": r.report_type,
            "operating_cash_inflow": str(r.operating_cash_inflow) if r.operating_cash_inflow else None,
            "operating_cash_outflow": str(r.operating_cash_outflow) if r.operating_cash_outflow else None,
            "operating_cash_net": str(r.operating_cash_net) if r.operating_cash_net else None,
            "sales_cash_received": str(r.sales_cash_received) if r.sales_cash_received else None,
            "investing_cash_net": str(r.investing_cash_net) if r.investing_cash_net else None,
            "financing_cash_net": str(r.financing_cash_net) if r.financing_cash_net else None,
            "capital_expenditure": str(r.capital_expenditure) if r.capital_expenditure else None,
            "free_cash_flow": str(r.free_cash_flow) if r.free_cash_flow else None,
            "cash_ending_balance": str(r.cash_ending_balance) if r.cash_ending_balance else None,
        }
    return ok(_paginate_query(q, page, page_size, to_item))


@router.get("/stocks/{stock_code}/indicators")
def get_indicators(
    stock_code: str,
    report_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(FinIndicator).filter(FinIndicator.stock_code == stock_code)
    if report_type:
        q = q.filter(FinIndicator.report_type == report_type)
    q = q.order_by(FinIndicator.report_date.desc())

    def to_item(r):
        return {
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "report_type": r.report_type,
            "roe": str(r.roe) if r.roe else None,
            "roa": str(r.roa) if r.roa else None,
            "net_margin": str(r.net_margin) if r.net_margin else None,
            "debt_to_assets": str(r.debt_to_assets) if r.debt_to_assets else None,
            "current_ratio": str(r.current_ratio) if r.current_ratio else None,
            "quick_ratio": str(r.quick_ratio) if r.quick_ratio else None,
            "ar_turnover": str(r.ar_turnover) if r.ar_turnover else None,
            "inventory_turnover": str(r.inventory_turnover) if r.inventory_turnover else None,
            "total_asset_turnover": str(r.total_asset_turnover) if r.total_asset_turnover else None,
            "operating_cycle": str(r.operating_cycle) if r.operating_cycle else None,
            "revenue_yoy": str(r.revenue_yoy) if r.revenue_yoy else None,
            "net_profit_yoy": str(r.net_profit_yoy) if r.net_profit_yoy else None,
            "cf_to_net_profit": str(r.cf_to_net_profit) if r.cf_to_net_profit else None,
            "sales_cash_ratio": str(r.sales_cash_ratio) if r.sales_cash_ratio else None,
        }
    return ok(_paginate_query(q, page, page_size, to_item))


# ========== 公司基本信息汇总 ==========

@router.get("/stocks/{stock_code}/overview")
def get_overview(stock_code: str, db: Session = Depends(get_db)):
    """公司基础信息 + 最新年报关键指标。"""
    basic = db.query(StockBasic).filter(StockBasic.stock_code == stock_code).first()
    if basic is None:
        raise NotFoundError(f"未找到股票: {stock_code}")

    # 最新 Annual 的关键指标
    latest = (
        db.query(FinIndicator)
        .filter(FinIndicator.stock_code == stock_code, FinIndicator.report_type == "Annual")
        .order_by(FinIndicator.report_date.desc())
        .first()
    )
    latest_income = (
        db.query(IncomeStatement)
        .filter(IncomeStatement.stock_code == stock_code, IncomeStatement.report_type == "Annual")
        .order_by(IncomeStatement.report_date.desc())
        .first()
    )
    latest_balance = (
        db.query(BalanceSheet)
        .filter(BalanceSheet.stock_code == stock_code, BalanceSheet.report_type == "Annual")
        .order_by(BalanceSheet.report_date.desc())
        .first()
    )

    return ok({
        "basic": {
            "stock_code": basic.stock_code,
            "stock_name": basic.stock_name,
            "industry": basic.industry,
            "market": basic.market,
        },
        "latest_annual": {
            "report_date": latest.report_date.isoformat() if latest else None,
            "roe": str(latest.roe) if latest and latest.roe else None,
            "roa": str(latest.roa) if latest and latest.roa else None,
            "debt_to_assets": str(latest.debt_to_assets) if latest and latest.debt_to_assets else None,
            "total_revenue": str(latest_income.total_revenue) if latest_income and latest_income.total_revenue else None,
            "net_profit_parent": str(latest_income.net_profit_parent) if latest_income and latest_income.net_profit_parent else None,
            "total_assets": str(latest_balance.total_assets) if latest_balance and latest_balance.total_assets else None,
        },
    })
