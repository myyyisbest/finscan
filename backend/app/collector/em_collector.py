"""东方财富财务数据采集器。

使用 akshare 的东方财富接口获取三大报表+主要财务指标，存入数据库：
- balance: stock_balance_sheet_by_report_em
- income: stock_profit_sheet_by_report_em
- cashflow: stock_cash_flow_sheet_by_report_em
- indicators: stock_financial_analysis_indicator_em (主要财务指标，含ROE等)
"""
from __future__ import annotations

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from app.db import db_session
from app.models import (
    StockBasic, FinReport, FinMainIndicator, CollectTaskLog, Watchlist, User,
    Announcement,
)

log = logging.getLogger("collector.em")


def _to_decimal(v) -> Optional[Decimal]:
    """将值转Decimal，None/无效值返回None。"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        try:
            return Decimal(str(v))
        except Exception:
            return None
    s = str(v).strip().replace(",", "")
    if s in ("", "--", "-", "nan", "None"):
        return None
    try:
        if s.endswith("%"):
            return Decimal(s[:-1])
        return Decimal(s)
    except Exception:
        return None


def _to_date(v) -> Optional[date]:
    """将时间字符串/对象转为date。"""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def _report_type_from_date(d: date) -> str:
    m = d.month
    if m == 3:
        return "Q1"
    if m == 6:
        return "H1"
    if m == 9:
        return "Q3"
    return "Annual"


# 东财主要财务指标的 ROE 为年化值，需按报告期还原为实际单期值
_ROE_ANNUALIZE_FACTOR = {"Q1": 4, "H1": 2, "Q3": Decimal(4) / Decimal(3), "Annual": 1}


def _deannualize_roe(roe: Decimal | None, report_type: str) -> Decimal | None:
    """将年化ROE还原为实际报告期的单期ROE。"""
    if roe is None:
        return None
    factor = _ROE_ANNUALIZE_FACTOR.get(report_type, 1)
    if factor == 1:
        return roe
    return roe / factor


def _detect_market(code: str) -> str:
    """根据股票代码推断市场 SH/SZ/BJ。"""
    if code.startswith(("60", "68", "90")):
        return "SH"
    if code.startswith(("00", "30", "20")):
        return "SZ"
    if code.startswith(("8", "4")):
        return "BJ"
    return "SZ"


def collect_stock_basic(code: str, stock_name: str = None):
    """确保股票基础信息存在。"""
    with db_session() as session:
        existing = session.query(StockBasic).filter(StockBasic.stock_code == code).first()
        if existing:
            if stock_name and (not existing.stock_name or existing.stock_name == code):
                existing.stock_name = stock_name
            session.commit()
            return existing
        market = _detect_market(code)
        s = StockBasic(
            stock_code=code,
            market=market,
            secucode=f"{market}{code}",
            stock_name=stock_name or code,
        )
        session.add(s)
        session.commit()
        return s


def collect_stock_data(code: str, stock_name: str = None) -> int:
    """采集单只股票的全部财务数据。返回写入的报告期数量。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")

    collect_stock_basic(code, stock_name)

    import akshare as ak
    import pandas as pd

    secucode = f"{_detect_market(code)}{code}"
    log.info("[%s] 开始采集 %s", code, secucode)

    balance_df = None
    income_df = None
    cashflow_df = None
    indicator_df = None

    # 资产负债表
    _update_log(code, "balance", "collecting")
    try:
        balance_df = ak.stock_balance_sheet_by_report_em(symbol=secucode)
        log.info("[%s] 资产负债表 %d 行", code, len(balance_df) if balance_df is not None else 0)
        _update_log(code, "balance", "done", report_count=len(balance_df) if balance_df is not None else 0)
    except Exception as e:
        log.warning("[%s] 资产负债表采集失败: %s", code, e)
        _update_log(code, "balance", "failed", str(e))

    # 利润表
    _update_log(code, "income", "collecting")
    try:
        income_df = ak.stock_profit_sheet_by_report_em(symbol=secucode)
        log.info("[%s] 利润表 %d 行", code, len(income_df) if income_df is not None else 0)
        _update_log(code, "income", "done", report_count=len(income_df) if income_df is not None else 0)
    except Exception as e:
        log.warning("[%s] 利润表采集失败: %s", code, e)
        _update_log(code, "income", "failed", str(e))

    # 现金流量表
    _update_log(code, "cashflow", "collecting")
    try:
        cashflow_df = ak.stock_cash_flow_sheet_by_report_em(symbol=secucode)
        log.info("[%s] 现金流量表 %d 行", code, len(cashflow_df) if cashflow_df is not None else 0)
        _update_log(code, "cashflow", "done", report_count=len(cashflow_df) if cashflow_df is not None else 0)
    except Exception as e:
        log.warning("[%s] 现金流量表采集失败: %s", code, e)
        _update_log(code, "cashflow", "failed", str(e))

    # 主要财务指标（含ROE等）
    _update_log(code, "indicator", "collecting")
    try:
        indicator_df = ak.stock_financial_analysis_indicator(symbol=secucode)
        log.info("[%s] 主要指标 %d 行", code, len(indicator_df) if indicator_df is not None else 0)
        _update_log(code, "indicator", "done", report_count=len(indicator_df) if indicator_df is not None else 0)
    except Exception as e:
        try:
            indicator_df = ak.stock_financial_analysis_indicator_em(symbol=secucode)
            log.info("[%s] 主要指标(em) %d 行", code, len(indicator_df) if indicator_df is not None else 0)
            _update_log(code, "indicator", "done", report_count=len(indicator_df) if indicator_df is not None else 0)
        except Exception as e2:
            log.warning("[%s] 主要指标采集失败: %s / %s", code, e, e2)
            _update_log(code, "indicator", "failed", str(e2))

    # 合并三表按报告期写入
    report_data = {}  # report_date_str -> {balance/income/cashflow: row_dict}

    if balance_df is not None:
        for _, row in balance_df.iterrows():
            rd = _to_date(row.get("REPORT_DATE"))
            if not rd:
                continue
            key = str(rd)
            if key not in report_data:
                report_data[key] = {}
            report_data[key]["balance"] = row.to_dict()
            if "report_name" not in report_data[key]:
                report_data[key]["report_name"] = row.get("REPORT_DATE_NAME", "")
            if "notice_date" not in report_data[key]:
                report_data[key]["notice_date"] = _to_date(row.get("NOTICE_DATE"))

    if income_df is not None:
        for _, row in income_df.iterrows():
            rd = _to_date(row.get("REPORT_DATE"))
            if not rd:
                continue
            key = str(rd)
            if key not in report_data:
                report_data[key] = {}
            report_data[key]["income"] = row.to_dict()
            if "report_name" not in report_data[key]:
                report_data[key]["report_name"] = row.get("REPORT_DATE_NAME", "")
            if "notice_date" not in report_data[key]:
                report_data[key]["notice_date"] = _to_date(row.get("NOTICE_DATE"))

    if cashflow_df is not None:
        for _, row in cashflow_df.iterrows():
            rd = _to_date(row.get("REPORT_DATE"))
            if not rd:
                continue
            key = str(rd)
            if key not in report_data:
                report_data[key] = {}
            report_data[key]["cashflow"] = row.to_dict()

    # 解析主要指标数据（按日期索引）
    indicator_map = {}
    if indicator_df is not None:
        for _, row in indicator_df.iterrows():
            rd = _to_date(row.get("日期"))
            if rd:
                indicator_map[str(rd)] = row.to_dict()

    written = 0
    with db_session() as session:
        # 用于同比计算：按报告期收集数据后计算同比
        date_to_report_obj = {}

        for key, data in report_data.items():
            rd = _to_date(key)
            report_name = data.get("report_name", "")
            notice_date = data.get("notice_date")
            report_type = _report_type_from_date(rd)

            obj = session.query(FinReport).filter(
                FinReport.stock_code == code, FinReport.report_date == rd
            ).first()
            if obj is None:
                obj = FinReport(
                    stock_code=code, report_date=rd, report_type=report_type,
                    report_name=report_name, notice_date=notice_date,
                )
                session.add(obj)
            else:
                obj.report_name = report_name
                if notice_date:
                    obj.notice_date = notice_date
                obj.report_type = report_type

            # 存JSON原始数据
            if "balance" in data:
                obj.balance_json = _clean_dict(data["balance"])
                _extract_balance_fields(obj, data["balance"])
            if "income" in data:
                obj.income_json = _clean_dict(data["income"])
                _extract_income_fields(obj, data["income"])
            if "cashflow" in data:
                obj.cashflow_json = _clean_dict(data["cashflow"])
                _extract_cashflow_fields(obj, data["cashflow"])

            # 应用主要指标（ROE等优先用东财直接数据）
            # 注意：东财主要指标的 ROE 为年化值，需还原为实际单期值
            if key in indicator_map:
                ind = indicator_map[key]
                raw_roe = _to_decimal(ind.get("净资产收益率(%)"))
                obj.roe = _deannualize_roe(raw_roe, report_type) if raw_roe is not None else obj.roe
                obj.roa = _to_decimal(ind.get("总资产利润率(%)")) or obj.roa
                obj.gross_margin = _to_decimal(ind.get("销售毛利率(%)")) or obj.gross_margin
                obj.net_margin = _to_decimal(ind.get("销售净利率(%)")) or obj.net_margin
                current_ratio = _to_decimal(ind.get("流动比率"))
                quick_ratio = _to_decimal(ind.get("速动比率"))
                if current_ratio:
                    obj.current_ratio = current_ratio
                if quick_ratio:
                    obj.quick_ratio = quick_ratio
                # 保存原始指标
                ind_obj = session.query(FinMainIndicator).filter(
                    FinMainIndicator.stock_code == code, FinMainIndicator.report_date == rd
                ).first()
                if ind_obj is None:
                    ind_obj = FinMainIndicator(
                        stock_code=code, report_date=rd, report_type=report_type,
                    )
                    session.add(ind_obj)
                ind_obj.raw_json = _clean_dict(ind)

            date_to_report_obj[key] = obj
            written += 1

        # 计算同比增长率（需要上年同期）
        _calc_yoy_growth(date_to_report_obj)

        session.commit()

    log.info("[%s] 写入 %d 期报表数据", code, written)
    return written


def collect_watchlist_data(user_id: int):
    """采集指定用户自选股的财务数据。"""
    with db_session() as session:
        stocks = (
            session.query(Watchlist)
            .filter(Watchlist.user_id == user_id)
            .all()
        )
        # 在session内取出需要的数据，避免DetachedInstanceError
        stock_list = [(w.stock_code, w.stock_name) for w in stocks]
    log.info("开始采集用户 %d 的 %d 只自选股", user_id, len(stock_list))
    for code, name in stock_list:
        try:
            collect_stock_data(code, name)
        except Exception as e:
            log.error("[%s] 采集失败: %s", code, e)


def _clean_dict(d: dict) -> dict:
    """清理DataFrame row转为的dict（处理NaN等不可序列化值）。"""
    import math
    out = {}
    for k, v in d.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            continue
        if v is not None:
            out[k] = v if not isinstance(v, (datetime, date)) else str(v)
    return out


def _extract_balance_fields(obj: FinReport, row: dict):
    """从资产负债表原始数据提取关键字段。"""
    obj.total_assets = _to_decimal(row.get("TOTAL_ASSETS"))
    obj.total_liabilities = _to_decimal(row.get("TOTAL_LIABILITIES"))
    total_parent_equity = _to_decimal(row.get("TOTAL_PARENT_EQUITY"))
    total_equity = _to_decimal(row.get("TOTAL_EQUITY"))
    obj.total_equity = total_parent_equity or total_equity

    # 每股相关
    share_capital = _to_decimal(row.get("SHARE_CAPITAL"))
    try:
        if share_capital is not None and share_capital > Decimal("0"):
            if total_parent_equity is not None:
                obj.bps = total_parent_equity / share_capital
            capital_reserve = _to_decimal(row.get("CAPITAL_RESERVE"))
            unassign = _to_decimal(row.get("UNASSIGN_RPOFIT"))
            if capital_reserve is not None:
                obj.capital_reserve_ps = capital_reserve / share_capital
            if unassign is not None:
                obj.undistr_profit_ps = unassign / share_capital
    except Exception:
        pass

    # 资产负债率
    ta = obj.total_assets
    tl = obj.total_liabilities
    try:
        if ta is not None and tl is not None and ta > Decimal("0"):
            obj.debt_ratio = tl / ta * Decimal("100")
    except Exception:
        pass

    # 流动比率/速动比率（如果主要指标接口没返回，这里近似计算）
    try:
        tca = _to_decimal(row.get("TOTAL_CURRENT_ASSETS"))
        tcl = _to_decimal(row.get("TOTAL_CURRENT_LIAB"))
        inventory = _to_decimal(row.get("INVENTORY"))
        if tca is not None and tcl is not None and tcl > Decimal("0"):
            if not obj.current_ratio:
                obj.current_ratio = tca / tcl
            if inventory is not None and not obj.quick_ratio:
                obj.quick_ratio = (tca - inventory) / tcl
    except Exception:
        pass


def _extract_income_fields(obj: FinReport, row: dict):
    """从利润表原始数据提取关键字段。"""
    obj.total_revenue = _to_decimal(row.get("TOTAL_OPERATE_INCOME"))
    obj.operate_profit = _to_decimal(row.get("OPERATE_PROFIT"))
    obj.total_profit = _to_decimal(row.get("TOTAL_PROFIT"))
    obj.net_profit = _to_decimal(row.get("NETPROFIT"))
    obj.net_profit_parent = _to_decimal(row.get("PARENT_NETPROFIT"))
    obj.deduct_net_profit = _to_decimal(row.get("DEDUCT_PARENT_NETPROFIT"))

    # EPS
    obj.eps = _to_decimal(row.get("BASIC_EPS"))

    # 毛利率 = (营收-营业成本)/营收
    rev = obj.total_revenue
    cost = _to_decimal(row.get("OPERATE_COST"))
    try:
        if rev is not None and rev > Decimal("0"):
            if cost is not None and not obj.gross_margin:
                obj.gross_margin = (rev - cost) / rev * Decimal("100")
    except Exception:
        pass

    # 净利率：归母净利润/营收
    npp = obj.net_profit_parent or obj.net_profit
    try:
        if rev is not None and rev > Decimal("0") and npp is not None and not obj.net_margin:
            obj.net_margin = npp / rev * Decimal("100")
    except Exception:
        pass


def _extract_cashflow_fields(obj: FinReport, row: dict):
    """从现金流量表提取关键字段。"""
    obj.operate_cash_net = _to_decimal(row.get("NETCASH_OPERATE"))


def _calc_yoy_growth(date_to_obj: dict):
    """计算同比增长率：本年同期 vs 上年同期。"""
    for key, obj in date_to_obj.items():
        try:
            rd = obj.report_date
            prev_year_key = f"{rd.year - 1}-{rd.month:02d}-{rd.day:02d}"
            prev_obj = date_to_obj.get(prev_year_key)
            if prev_obj is None:
                continue

            # 营收同比
            try:
                if (obj.total_revenue is not None and prev_obj.total_revenue is not None
                    and abs(prev_obj.total_revenue) > Decimal("0")):
                    obj.revenue_yoy = (obj.total_revenue - prev_obj.total_revenue) / abs(prev_obj.total_revenue) * Decimal("100")
            except Exception:
                pass

            # 归母净利润同比
            try:
                if (obj.net_profit_parent is not None and prev_obj.net_profit_parent is not None
                    and abs(prev_obj.net_profit_parent) > Decimal("0")):
                    obj.net_profit_yoy = (obj.net_profit_parent - prev_obj.net_profit_parent) / abs(prev_obj.net_profit_parent) * Decimal("100")
            except Exception:
                pass

            # 总资产同比
            try:
                if (obj.total_assets is not None and prev_obj.total_assets is not None
                    and abs(prev_obj.total_assets) > Decimal("0")):
                    obj.assets_yoy = (obj.total_assets - prev_obj.total_assets) / abs(prev_obj.total_assets) * Decimal("100")
            except Exception:
                pass

            # ROA 简单计算：净利润/总资产（年化）
            try:
                if obj.roa is None and obj.net_profit_parent is not None and obj.total_assets is not None and obj.total_assets > Decimal("0"):
                    quarter_map = {"Q1": 4, "H1": 2, "Q3": Decimal(4) / Decimal(3), "Annual": 1}
                    factor = quarter_map.get(obj.report_type, 1)
                    annual_np = obj.net_profit_parent * Decimal(str(factor))
                    obj.roa = annual_np / obj.total_assets * Decimal("100")
            except Exception:
                pass

            # ROE 年化计算（如果主要指标接口没有数据）
            try:
                if obj.roe is None and obj.net_profit_parent is not None and obj.total_equity is not None and obj.total_equity > Decimal("0"):
                    quarter_map = {"Q1": 4, "H1": 2, "Q3": Decimal(4) / Decimal(3), "Annual": 1}
                    factor = quarter_map.get(obj.report_type, 1)
                    annual_np = obj.net_profit_parent * Decimal(str(factor))
                    obj.roe = annual_np / obj.total_equity * Decimal("100")
            except Exception:
                pass

        except (ValueError, TypeError, ZeroDivisionError, AttributeError):
            continue


def _update_log(code: str, task_type: str, status: str, error_msg: str = None, report_count: int = 0):
    """更新采集日志。"""
    try:
        with db_session() as session:
            log_entry = session.query(CollectTaskLog).filter(
                CollectTaskLog.stock_code == code,
                CollectTaskLog.task_type == task_type,
            ).first()
            if log_entry is None:
                log_entry = CollectTaskLog(
                    stock_code=code, task_type=task_type, status=status,
                    error_msg=error_msg, report_count=report_count,
                    last_attempt=datetime.now(),
                )
                session.add(log_entry)
            else:
                log_entry.status = status
                log_entry.error_msg = error_msg
                log_entry.report_count = report_count
                log_entry.last_attempt = datetime.now()
            session.commit()
    except Exception as e:
        log.warning("更新采集日志失败: %s", e)


def collect_announcements(code: str, days: int = 180) -> int:
    """采集单只股票的公告数据，存入 Announcement 表（只保存链接）。返回新增条数。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    import akshare as ak
    from datetime import datetime, timedelta

    _update_log(code, "announcement", "collecting")
    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        df = ak.stock_individual_notice_report(
            security=code,
            symbol="全部",
            begin_date=start_date,
            end_date=end_date,
        )
        if df is None or len(df) == 0:
            _update_log(code, "announcement", "done", report_count=0)
            return 0

        added = 0
        with db_session() as session:
            for _, row in df.iterrows():
                url = str(row.get("网址", "")).strip()
                pub_date = _to_date(row.get("公告日期"))
                if not url or not pub_date:
                    continue

                # 只通过链接去重
                existing = session.query(Announcement).filter(
                    Announcement.stock_code == code,
                    Announcement.pdf_url == url,
                ).first()
                if existing:
                    # 更新标题和类型（如果有的话）
                    if not existing.ann_title:
                        title = str(row.get("公告标题", "")).strip()
                        if title and title != "nan":
                            existing.ann_title = title
                            existing.ann_type = str(row.get("公告类型", "")) or None
                            session.commit()
                    continue

                ann = Announcement(
                    stock_code=code,
                    ann_title=None,  # 不保存标题文字
                    ann_type=None,   # 不保存类型
                    publish_date=pub_date,
                    pdf_url=url,
                    source="eastmoney",
                )
                session.add(ann)
                added += 1
            session.commit()

        _update_log(code, "announcement", "done", report_count=added)
        log.info("[%s] 公告采集完成，新增 %d 条", code, added)
        return added
    except Exception as e:
        log.warning("[%s] 公告采集失败: %s", code, e)
        _update_log(code, "announcement", "failed", str(e))
        return 0


def collect_company_profile(code: str) -> bool:
    """采集公司简介，更新 StockBasic 表的扩展信息。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    import akshare as ak

    _update_log(code, "profile", "collecting")
    try:
        df = ak.stock_profile_cninfo(symbol=code)
        if df is None or len(df) == 0:
            _update_log(code, "profile", "done")
            return False

        row = df.iloc[0]
        with db_session() as session:
            stock = session.query(StockBasic).filter(StockBasic.stock_code == code).first()
            if stock:
                full_name = str(row.get("公司名称", "")).strip()
                industry = str(row.get("所属行业", "")).strip()
                list_date = _to_date(row.get("上市日期"))
                if full_name and full_name != "nan":
                    stock.full_name = full_name
                if industry and industry != "nan":
                    stock.industry = industry
                if list_date:
                    stock.list_date = list_date
                session.commit()

        _update_log(code, "profile", "done")
        log.info("[%s] 公司简介采集完成", code)
        return True
    except Exception as e:
        log.warning("[%s] 公司简介采集失败: %s", code, e)
        _update_log(code, "profile", "failed", str(e))
        return False


def collect_stock_full(code: str, stock_name: str = None) -> int:
    """完整采集：财务数据 + 公告 + 公司简介。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    report_count = collect_stock_data(code, stock_name)
    try:
        collect_company_profile(code)
    except Exception as e:
        log.warning("[%s] 公司简介采集异常: %s", code, e)
    try:
        collect_announcements(code)
    except Exception as e:
        log.warning("[%s] 公告采集异常: %s", code, e)
    return report_count


def collect_watchlist_full(user_id: int):
    """完整采集用户自选股：财务 + 公告 + 简介。"""
    with db_session() as session:
        stocks = (
            session.query(Watchlist)
            .filter(Watchlist.user_id == user_id)
            .all()
        )
        stock_list = [(w.stock_code, w.stock_name) for w in stocks]
    log.info("开始完整采集用户 %d 的 %d 只自选股", user_id, len(stock_list))
    for code, name in stock_list:
        try:
            collect_stock_full(code, name)
        except Exception as e:
            log.error("[%s] 完整采集失败: %s", code, e)
