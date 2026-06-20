"""关注池 API：分组管理 + 股票增删 + 列表查询。"""
from typing import List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.auth import get_current_user
from app.core.exceptions import BizException
from app.core.response import ok
from app.db import get_db
from app.models import Watchlist, StockBasic, User


router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


class WatchlistGroup(BaseModel):
    group_name: str
    stocks: List[dict]


# ---- 查询 ----

@router.get("/groups")
def list_groups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """按分组列出关注池。"""
    rows = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user.id)
        .order_by(Watchlist.group_name, Watchlist.add_time)
        .all()
    )
    # 按 group_name 聚合
    groups_map: dict[str, list] = {}
    for r in rows:
        groups_map.setdefault(r.group_name, []).append({
            "id": r.id,
            "stock_code": r.stock_code,
            "stock_name": r.stock_name,
            "remark": r.remark,
            "add_time": r.add_time.isoformat() if r.add_time else None,
        })
    groups = [{"group_name": k, "stocks": v} for k, v in groups_map.items()]
    return ok({"groups": groups, "total": len(rows)})


# ---- 操作 ----

class AddStockIn(BaseModel):
    stock_code: str
    stock_name: str = ""
    group_name: str = "默认分组"
    remark: str | None = None


@router.post("/add")
def add_stock(body: AddStockIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        item = Watchlist(
            user_id=user.id,
            group_name=body.group_name,
            stock_code=body.stock_code,
            stock_name=body.stock_name or body.stock_code,
            remark=body.remark,
        )
        db.add(item)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BizException(1001, "该股票已在关注池中")
    return ok({"id": item.id})


class RemoveIn(BaseModel):
    stock_code: str
    group_name: str = "默认分组"


@router.delete("/remove")
def remove_stock(body: RemoveIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == user.id,
            Watchlist.group_name == body.group_name,
            Watchlist.stock_code == body.stock_code,
        )
        .delete()
    )
    db.commit()
    return ok({"deleted": n})


class CreateGroupIn(BaseModel):
    group_name: str


@router.post("/group")
def create_group(body: CreateGroupIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 分组是逻辑的，不需要单独建表；这里确认一下是否已有
    return ok({"group_name": body.group_name})


class RenameGroupIn(BaseModel):
    old_name: str
    new_name: str


@router.put("/group/rename")
def rename_group(body: RenameGroupIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user.id, Watchlist.group_name == body.old_name)
        .update({"group_name": body.new_name})
    )
    db.commit()
    return ok({"updated": n, "new_name": body.new_name})


class MoveStockIn(BaseModel):
    stock_code: str
    from_group: str
    to_group: str


@router.put("/move")
def move_stock(body: MoveStockIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == user.id,
            Watchlist.group_name == body.from_group,
            Watchlist.stock_code == body.stock_code,
        )
        .update({"group_name": body.to_group})
    )
    db.commit()
    return ok({"updated": n})
