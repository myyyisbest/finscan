"""风险排雷 API。"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_optional_user_id
from app.core.response import ok
from app.db import get_db
from app.models import Watchlist, RiskReport, RiskRuleResult
from app.risk import RiskEngine


router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("/stocks/{stock_code}/report")
def get_risk_report(
    stock_code: str,
    report_date: str = Query(description="报告期 YYYY-MM-DD，默认最新年报"),
    db: Session = Depends(get_db),
):
    """获取单公司风险报告（存在则返回，不存在则触发实时计算）。"""
    # 解析日期
    try:
        d = date.fromisoformat(report_date[:10])
    except ValueError:
        d = None

    # 先查库
    q = db.query(RiskReport).filter(RiskReport.stock_code == stock_code)
    if d:
        q = q.filter(RiskReport.report_date == d)
    report = q.order_by(RiskReport.report_date.desc()).first()

    if report is None:
        # 实时计算
        engine = RiskEngine(db)
        report = engine.evaluate(stock_code, report_date)
        # 报告已经是 upsert，规则结果在 engine 里已经处理

    # 读取规则明细
    rules = (
        db.query(RiskRuleResult)
        .filter(RiskRuleResult.stock_code == stock_code,
                RiskRuleResult.report_date == report.report_date)
        .all()
    )

    return ok({
        "stock_code": report.stock_code,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "total_score": str(report.total_score),
        "risk_level": report.risk_level,
        "rule_total": report.rule_total,
        "rule_participated": report.rule_participated,
        "data_completeness": str(report.data_completeness),
        "rules": [
            {
                "rule_code": r.rule_code,
                "result": r.result,
                "score": str(r.score),
                "evidence": r.evidence,
            }
            for r in rules
        ],
    })


class BatchEvaluateIn(BaseModel):
    stock_codes: list[str]
    report_date: str | None = None


@router.post("/batch")
def batch_evaluate(
    body: BatchEvaluateIn,
    db: Session = Depends(get_db),
):
    """批量排雷（最多 50 只）。"""
    if len(body.stock_codes) > 50:
        return {"code": 1001, "message": "最多支持50只股票批量排雷"}
    report_date = date.fromisoformat(body.report_date[:10]) if body.report_date else date(2025, 12, 31)
    engine = RiskEngine(db)
    reports = engine.batch_evaluate(body.stock_codes, report_date)
    return ok([
        {
            "stock_code": r.stock_code,
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "total_score": str(r.total_score),
            "risk_level": r.risk_level,
        }
        for r in reports
    ])


@router.get("/my-batch")
def my_batch_risk(
    group_name: str = Query("默认分组"),
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
):
    """对当前用户关注池执行批量排雷。"""
    if user_id is None:
        return ok([])
    watchlist = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.group_name == group_name)
        .all()
    )
    codes = [w.stock_code for w in watchlist]
    if not codes:
        return ok([])
    engine = RiskEngine(db)
    reports = engine.batch_evaluate(codes, date(2025, 12, 31))
    return ok([
        {
            "stock_code": r.stock_code,
            "total_score": str(r.total_score),
            "risk_level": r.risk_level,
        }
        for r in reports
    ])
