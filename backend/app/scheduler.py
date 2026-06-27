"""finscan 定时调度任务。

调度时间（PRD 第八章第三节）：
  - 每日 02:00 财报增量同步
  - 每日 03:00 公告增量同步
  - 每日 04:00 财务指标预计算 + 排雷预计算
  - 每周一 01:00 全量数据完整性校验

用法：
  from app.scheduler import start_scheduler, shutdown_scheduler
  start_scheduler()  # 在 FastAPI lifespan 中调用
"""
from datetime import datetime, date
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logger import get_logger


log = get_logger("scheduler")
_scheduler: BackgroundScheduler | None = None


def _incremental_collect():
    """每日增量采集：抓取最近新增财报。"""
    from app.collector.sina_adapter import collect_one_stock, _record_task_log
    from app.collector.em_indicator import collect_indicators
    from app.models import CollectTaskLog
    from app.db import db_session
    log.info("[Scheduler] 开始增量采集")
    today = date.today()
    try:
        # 查找近7日内未完成的采集任务
        from datetime import timedelta
        cutoff = today - timedelta(days=7)
        with db_session() as session:
            pending = (
                session.query(CollectTaskLog)
                .filter(CollectTaskLog.status.in_(["pending", "failed"]),
                        CollectTaskLog.last_attempt == None)  # noqa: E711
                .limit(50)
                .all()
            )
            codes = list({p.stock_code for p in pending})
        log.info("[Scheduler] 待采集股票: %d", len(codes))
        for code in codes:
            try:
                collect_one_stock(code)
                collect_indicators(code)
            except Exception as exc:  # noqa: BLE001
                log.warning("[Scheduler] 增量采集 %s 失败: %s", code, exc)
    except Exception as exc:  # noqa: BLE001
        log.error("[Scheduler] 增量采集异常: %s", exc)


def _calc_risk_reports():
    """每日排雷预计算：所有已有关注池股票。"""
    from app.risk import RiskEngine
    from app.models import StockBasic, RiskReport
    from app.db import db_session
    log.info("[Scheduler] 开始排雷预计算")
    today = date.today()
    # 用最新年报日期
    report_date = date(today.year - 1, 12, 31) if today.month < 5 else date(today.year, 12, 31)
    try:
        with db_session() as session:
            codes = [s.stock_code for s in session.query(StockBasic).all()]
        engine = RiskEngine(db_session().__enter__())
        engine.session = db_session().__enter__()
        reports = engine.batch_evaluate(codes, report_date)
        log.info("[Scheduler] 排雷完成: %d 只股票", len(reports))
    except Exception as exc:  # noqa: BLE001
        log.error("[Scheduler] 排雷预计算异常: %s", exc)


def _calc_industry_medians():
    """定期计算行业中位值。"""
    from app.models import StockBasic
    from app.db import db_session
    log.info("[Scheduler] 开始行业中位值计算")
    try:
        with db_session() as session:
            industries = {s.industry for s in session.query(StockBasic).all() if s.industry}
        for industry in industries:
            if not industry:
                continue
            try:
                from app.api.compare import calc_industry_median
                calc_industry_median(industry=industry, report_type="Annual")
            except (ImportError, AttributeError):
                pass
        log.info("[Scheduler] 行业中位值计算完成: %d 个行业", len(industries))
    except Exception as exc:  # noqa: BLE001
        log.error("[Scheduler] 行业中位值异常: %s", exc)


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai", daemon=True)

    # 每日 02:00 增量采集
    _scheduler.add_job(
        _incremental_collect,
        CronTrigger(hour=2, minute=0, timezone="Asia/Shanghai"),
        id="incremental_collect",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # 每日 04:00 排雷预计算
    _scheduler.add_job(
        _calc_risk_reports,
        CronTrigger(hour=4, minute=0, timezone="Asia/Shanghai"),
        id="calc_risk_reports",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # 每周一 01:00 行业中位值
    _scheduler.add_job(
        _calc_industry_medians,
        CronTrigger(day_of_week="mon", hour=1, minute=0, timezone="Asia/Shanghai"),
        id="calc_industry_medians",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    _scheduler.start()
    log.info("调度器已启动 (jobs: %s)", [j.id for j in _scheduler.get_jobs()])


def shutdown_scheduler():
    if _scheduler:
        _scheduler.shutdown(wait=False)
        log.info("调度器已关闭")
