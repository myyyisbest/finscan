"""自选股API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db import get_db
from app.core.auth import get_current_user
from app.core.response import success_response, fail_response
from app.models import Watchlist, User, StockBasic, FinReport

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
                "report_name": latest.report_name if latest else None,
                "total_revenue": float(latest.total_revenue) if latest and latest.total_revenue else None,
                "net_profit_parent": float(latest.net_profit_parent) if latest and latest.net_profit_parent else None,
                "roe": float(latest.roe) if latest and latest.roe else None,
                "debt_ratio": float(latest.debt_ratio) if latest and latest.debt_ratio else None,
                "revenue_yoy": float(latest.revenue_yoy) if latest and latest.revenue_yoy else None,
            } if latest else None,
        })
    return success_response(result)


@router.post("")
def add_stock(
    body: AddStockIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加股票到自选。"""
    code = body.stock_code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    if len(code) != 6 or not code.isdigit():
        return fail_response("股票代码格式错误")

    existing = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == current_user.id, Watchlist.stock_code == code)
        .first()
    )
    if existing:
        return fail_response("已在自选股中")

    # 如果未传名称，尝试从stock_basic获取
    name = body.stock_name
    if not name:
        stock = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
        name = stock.stock_name if stock else code

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
