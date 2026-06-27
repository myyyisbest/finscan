"""自选股API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db import get_db
from app.core.auth import get_current_user
from app.core.response import success_response, fail_response
from app.models import Watchlist, User, StockBasic, FinReport, FinMainIndicator

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


class AddStockIn(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    remark: Optional[str] = None


class RemoveStockIn(BaseModel):
    stock_code: str


@router.get("")
def list_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的自选股列表，附带最新财务概览。金额单位：元。"""
    items = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.add_time.desc())
        .all()
    )
    result = []
    for w in items:
        code = w.stock_code
        stock = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
        latest = (
            db.query(FinReport)
            .filter(FinReport.stock_code == code)
            .order_by(FinReport.report_date.desc())
            .first()
        )
        latest_ind = (
            db.query(FinMainIndicator)
            .filter(FinMainIndicator.stock_code == code)
            .order_by(FinMainIndicator.report_date.desc())
            .first()
        )

        # 从 JSON 提取关键指标（兼容新老数据）
        total_revenue = None
        net_profit_parent = None
        if latest:
            income = latest.income_json or {}
            total_revenue = (
                float(latest.total_revenue)
                if latest.total_revenue is not None
                else _safe_float(income.get("TOTAL_OPERATE_INCOME") or income.get("TOTALOPERATEREVE"))
            )
            net_profit_parent = (
                float(latest.net_profit_parent)
                if latest.net_profit_parent is not None
                else _safe_float(income.get("PARENT_NETPROFIT") or income.get("PARENTNETPROFIT"))
            )

        roe = None
        debt_ratio = None
        revenue_yoy = None
        if latest_ind and latest_ind.raw_json:
            raw = latest_ind.raw_json
            roe = _safe_float(raw.get("ROEJQ"))
            debt_ratio = _safe_float(raw.get("ZCFZL"))
            revenue_yoy = _safe_float(raw.get("TOTALOPERATEREVETZ"))
        elif latest:
            roe = float(latest.roe) if latest.roe is not None else None
            debt_ratio = float(latest.debt_ratio) if latest.debt_ratio is not None else None
            revenue_yoy = float(latest.revenue_yoy) if latest.revenue_yoy is not None else None

        result.append({
            "stock_code": code,
            "stock_name": w.stock_name or (stock.stock_name if stock else code),
            "market": stock.market if stock else "",
            "secucode": stock.secucode if stock else f"SZ{code}",
            "industry": stock.industry if stock else None,
            "remark": w.remark,
            "add_time": str(w.add_time),
            "latest_report": {
                "report_date": str(latest.report_date) if latest else None,
                "report_name": latest.report_name if latest else (
                    latest_ind.raw_json.get("REPORT_TYPE", "") if latest_ind and latest_ind.raw_json else None
                ),
                "total_revenue": total_revenue,
                "net_profit_parent": net_profit_parent,
                "roe": roe,
                "debt_ratio": debt_ratio,
                "revenue_yoy": revenue_yoy,
            } if latest or latest_ind else None,
        })
    return success_response(result)


def _safe_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


@router.post("")
def add_stock(
    body: AddStockIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加股票到自选。支持输入6位代码或股票名称。"""
    raw = body.stock_code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "").strip()

    from app.api.stock import _get_all_stocks, _detect_market
    all_stocks = _get_all_stocks()

    code = None
    name = body.stock_name or raw

    # 情况1：输入的是6位数字代码
    if len(raw) == 6 and raw.isdigit():
        code = raw
        # 从akshare列表查找名称
        for s_code, s_name in all_stocks:
            if s_code == code:
                name = s_name
                break
    else:
        # 情况2：输入的是名称，从akshare列表查找代码
        raw_clean = raw.replace(' ', '').replace('\u3000', '')
        for s_code, s_name in all_stocks:
            s_name_clean = s_name.replace(' ', '').replace('\u3000', '')
            if s_name_clean == raw_clean or raw_clean in s_name_clean:
                code = s_code
                name = s_name
                break

    if not code:
        return fail_response("未找到对应的股票，请确认输入正确的代码或名称")

    if len(code) != 6 or not code.isdigit():
        return fail_response("股票代码格式错误")

    existing = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == current_user.id, Watchlist.stock_code == code)
        .first()
    )
    if existing:
        return fail_response("已在自选股中")

    # 自动入库到stock_basic
    stock = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
    if not stock:
        market = _detect_market(code)
        stock = StockBasic(
            stock_code=code,
            market=market,
            secucode=f"{market}{code}",
            stock_name=name,
        )
        db.add(stock)
    elif not stock.stock_name or stock.stock_name == code:
        stock.stock_name = name

    w = Watchlist(
        user_id=current_user.id,
        stock_code=code,
        stock_name=name,
        remark=body.remark,
    )
    db.add(w)
    db.commit()
    return success_response({"stock_code": code, "stock_name": name})


@router.delete("/{code}")
def remove_stock(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从自选移除股票。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    w = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == current_user.id, Watchlist.stock_code == code)
        .first()
    )
    if not w:
        return fail_response("该股票不在自选股中")
    db.delete(w)
    db.commit()
    return success_response({"removed": code})
