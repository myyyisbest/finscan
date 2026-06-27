"""自选股API。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db import get_db
from app.core.auth import get_current_user
from app.core.response import success_response, fail_response
from app.models import Watchlist, WatchlistGroup, User, StockBasic, FinReport, FinMainIndicator

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


class AddStockIn(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    group_id: Optional[int] = None
    remark: Optional[str] = None


class RemoveStockIn(BaseModel):
    stock_code: str


class CreateGroupIn(BaseModel):
    name: str


class MoveStockIn(BaseModel):
    stock_code: str
    group_id: Optional[int] = None


@router.get("/groups")
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的自选分组列表。"""
    groups = (
        db.query(WatchlistGroup)
        .filter(WatchlistGroup.user_id == current_user.id)
        .order_by(WatchlistGroup.sort_order, WatchlistGroup.created_at)
        .all()
    )
    result = []
    for g in groups:
        count = db.query(Watchlist).filter(Watchlist.user_id == current_user.id, Watchlist.group_id == g.id).count()
        result.append({
            "id": g.id,
            "name": g.name,
            "sort_order": g.sort_order,
            "stock_count": count,
            "created_at": str(g.created_at),
        })
    return success_response(result)


@router.post("/groups")
def create_group(
    body: CreateGroupIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新的自选分组。"""
    name = body.name.strip()
    if not name:
        return fail_response("分组名称不能为空")
    if len(name) > 50:
        return fail_response("分组名称最多50个字符")

    # 检查是否重名
    existing = db.query(WatchlistGroup).filter(
        WatchlistGroup.user_id == current_user.id,
        WatchlistGroup.name == name
    ).first()
    if existing:
        return fail_response("分组名称已存在")

    max_order = db.query(WatchlistGroup.sort_order).filter(
        WatchlistGroup.user_id == current_user.id
    ).order_by(WatchlistGroup.sort_order.desc()).first()
    next_order = (max_order[0] + 1) if max_order else 0

    g = WatchlistGroup(user_id=current_user.id, name=name, sort_order=next_order)
    db.add(g)
    db.commit()
    return success_response({"id": g.id, "name": g.name, "sort_order": g.sort_order})


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除分组（组内股票移至默认分组）。"""
    g = db.query(WatchlistGroup).filter(
        WatchlistGroup.id == group_id,
        WatchlistGroup.user_id == current_user.id
    ).first()
    if not g:
        return fail_response("分组不存在")

    # 将组内股票移至默认分组（group_id=0）
    db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.group_id == group_id
    ).update({"group_id": 0})
    db.delete(g)
    db.commit()
    return success_response({"deleted": group_id})


@router.patch("/groups/{group_id}")
def rename_group(
    group_id: int,
    body: CreateGroupIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重命名分组。"""
    g = db.query(WatchlistGroup).filter(
        WatchlistGroup.id == group_id,
        WatchlistGroup.user_id == current_user.id
    ).first()
    if not g:
        return fail_response("分组不存在")
    g.name = body.name.strip()
    db.commit()
    return success_response({"id": g.id, "name": g.name})


@router.post("/move")
def move_stock(
    body: MoveStockIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将股票移动到指定分组。"""
    code = body.stock_code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    w = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.stock_code == code
    ).first()
    if not w:
        return fail_response("该股票不在自选股中")

    if body.group_id is not None and body.group_id > 0:
        # 验证分组存在
        g = db.query(WatchlistGroup).filter(
            WatchlistGroup.id == body.group_id,
            WatchlistGroup.user_id == current_user.id
        ).first()
        if not g:
            return fail_response("目标分组不存在")
    else:
        body.group_id = 0  # 默认分组

    w.group_id = body.group_id
    db.commit()
    return success_response({"stock_code": code, "group_id": body.group_id})


@router.get("")
def list_watchlist(
    group_id: int = Query(None, description="分组ID，不传则返回全部"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的自选股列表，附带最新财务概览。金额单位：元。"""
    query = db.query(Watchlist).filter(Watchlist.user_id == current_user.id)
    if group_id is not None:
        query = query.filter(Watchlist.group_id == group_id)
    items = query.order_by(Watchlist.add_time.desc()).all()
    result = []
    for w in items:
        code = w.stock_code
        stock = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
        # 只取最新年报数据（避免季报/年化数据干扰展示）
        latest = (
            db.query(FinReport)
            .filter(FinReport.stock_code == code, FinReport.report_type == "Annual")
            .order_by(FinReport.report_date.desc())
            .first()
        )
        latest_ind = (
            db.query(FinMainIndicator)
            .filter(FinMainIndicator.stock_code == code, FinMainIndicator.report_type == "Annual")
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
        net_profit_yoy = None
        if latest_ind and latest_ind.raw_json:
            raw = latest_ind.raw_json
            roe = _safe_float(raw.get("ROEJQ"))
            debt_ratio = _safe_float(raw.get("ZCFZL"))
            revenue_yoy = _safe_float(raw.get("TOTALOPERATEREVETZ"))
            net_profit_yoy = _safe_float(raw.get("PARENTNETPROFITTZ"))
        elif latest:
            roe = float(latest.roe) if latest.roe is not None else None
            debt_ratio = float(latest.debt_ratio) if latest.debt_ratio is not None else None
            revenue_yoy = float(latest.revenue_yoy) if latest.revenue_yoy is not None else None
            net_profit_yoy = float(latest.net_profit_yoy) if latest.net_profit_yoy is not None else None

        result.append({
            "stock_code": code,
            "stock_name": w.stock_name or (stock.stock_name if stock else code),
            "market": stock.market if stock else "",
            "secucode": stock.secucode if stock else f"SZ{code}",
            "industry": stock.industry if stock else None,
            "group_id": w.group_id or 0,
            "group_name": w.group.name if w.group else "默认分组",
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
                "net_profit_yoy": net_profit_yoy,
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
        group_id=body.group_id or 0,
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
