"""数据采集API：手动触发采集自选股或指定股票财务数据。"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db import get_db
from app.core.auth import get_current_user
from app.core.response import success_response, fail_response
from app.models import User

router = APIRouter(prefix="/api/v1/collector", tags=["collector"])


class CollectRequest(BaseModel):
    stock_code: Optional[str] = None
    scope: str = "watchlist"


@router.post("/trigger")
async def trigger_collect(
    body: CollectRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发数据采集任务。

    scope=watchlist: 采集当前用户的自选股
    scope=single: 采集指定单只股票
    """
    if body.scope == "single" and not body.stock_code:
        return fail_response("scope=single时必须提供stock_code")

    # 将采集任务放入后台执行
    from app.collector.em_collector import collect_stock_data, collect_watchlist_data

    if body.scope == "single":
        code = body.stock_code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
        background_tasks.add_task(collect_stock_data, code)
        return success_response({"task": f"collecting {code}", "status": "started"})
    else:
        user_id = current_user.id
        background_tasks.add_task(collect_watchlist_data, user_id)
        return success_response({"task": "collecting watchlist", "status": "started"})


@router.get("/status/{code}")
def get_collect_status(code: str, db: Session = Depends(get_db)):
    """查询某股票的采集状态。"""
    from app.models import CollectTaskLog, FinReport
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    logs = (
        db.query(CollectTaskLog)
        .filter(CollectTaskLog.stock_code == code)
        .order_by(CollectTaskLog.last_attempt.desc())
        .limit(10)
        .all()
    )
    report_count = db.query(FinReport).filter(FinReport.stock_code == code).count()
    return success_response({
        "stock_code": code,
        "report_count": report_count,
        "tasks": [{
            "task_type": l.task_type,
            "status": l.status,
            "report_count": l.report_count,
            "error_msg": l.error_msg,
            "last_attempt": str(l.last_attempt) if l.last_attempt else None,
        } for l in logs],
    })
