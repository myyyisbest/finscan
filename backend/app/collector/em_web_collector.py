"""东方财富 EM Web 数据采集器。

使用 akshare 调用东方财富接口获取财务数据：
- 主要指标: stock_financial_analysis_indicator_em (140+字段)
- 资产负债表: stock_balance_sheet_by_report_em (300+字段)
- 利润表: stock_profit_sheet_by_report_em (200+字段)
- 现金流量表: stock_cash_flow_sheet_by_report_em (250+字段)
"""
import time
import json
import logging
import math
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# 主要指标字段映射（东方财富字段 -> 数据库字段）
MAIN_INDICATOR_MAPPING = {
    # 每股指标
    "EPSJB": "eps",
    "EPSXS": "eps_diluted",
    "BPS": "bps",
    "MGZBGJ": "capital_reserve_ps",
    "MGWFPLR": "undistr_profit_ps",
    "MGJYXJJE": "operate_cash_ps",
    # 规模数据
    "TOTALOPERATEREVE": "total_revenue",
    "MLR": "gross_profit",
    "PARENTNETPROFIT": "net_profit_parent",
    "KCFJCXSYJLR": "deduct_net_profit",
    # 盈利能力
    "XSMLL": "gross_margin",
    "ROEJQ": "roe",
    "ROEKCJQ": "roe_diluted",
    "ZZCJLL": "roa",
    "XSJLL": "net_margin",
    # 偿债能力
    "ZCFZL": "debt_ratio",
    "LD": "current_ratio",
    "SD": "quick_ratio",
    "XJLLB": "cash_debt_ratio",
    # 运营能力
    "ZZCZZTS": "total_asset_turnover_days",
    "CHZZTS": "inventory_turnover_days",
    "YSZKZZTS": "receivable_turnover_days",
    "TOAZZL": "total_asset_turnover",
    "CHZZL": "inventory_turnover",
    "YSZKZZL": "receivable_turnover",
    # 成长能力（同比）
    "TOTALOPERATEREVETZ": "revenue_yoy",
    "PARENTNETPROFITTZ": "net_profit_yoy",
    "KCFJCXSYJLRTZ": "deduct_net_profit_yoy",
    # 资产
    "TOTAL_ASSETS": "total_assets",
    "TOTAL_LIABILITIES": "total_liabilities",
    "TOTAL_EQUITY": "total_equity",
}


def _to_decimal(value) -> Optional[Decimal]:
    """安全转换为Decimal"""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


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


def _get_secucode(code: str) -> str:
    """获取东财格式的代码（如SZ002130）"""
    return f"{_detect_market(code)}{code}"


def _get_ak_symbol(code: str) -> str:
    """获取akshare格式的代码（如002130.SZ）"""
    return f"{code}.{_detect_market(code)}"


def _parse_report_type(report_type: str) -> tuple[str, str]:
    """解析报告期类型"""
    rt = report_type or ""
    if "一季" in rt or "Q1" in rt:
        return "Q1", "Q1"
    elif "中报" in rt or "半年" in rt:
        return "H1", "H1"
    elif "三季" in rt or "Q3" in rt:
        return "Q3", "Q3"
    elif "年报" in rt or "年度" in rt:
        return "Annual", "Annual"
    return rt[:5] if rt else "Annual", "Annual"


def collect_main_indicators(code: str, secucode: str = None) -> list[dict]:
    """采集主要财务指标（使用akshare获取完整数据）"""
    ak_symbol = _get_ak_symbol(code)

    try:
        import akshare as ak
        df = ak.stock_financial_analysis_indicator_em(symbol=ak_symbol, indicator="按报告期")
        if df is not None and len(df) > 0:
            data = df.to_dict("records")
            # 清理 NaN 值和日期格式
            for row in data:
                for k, v in list(row.items()):
                    if isinstance(v, float) and math.isnan(v):
                        row[k] = None
                    elif hasattr(v, "strftime"):
                        row[k] = v.strftime("%Y-%m-%d")
            log.info("[%s] 主要指标: %d 期", code, len(data))
            return data
    except Exception as e:
        log.warning("[%s] 主要指标采集失败: %s", code, e)

    return []


def collect_income_statement(code: str, secucode: str = None) -> list[dict]:
    """采集利润表（使用akshare获取完整数据）"""
    ak_symbol = _get_ak_symbol(code)

    try:
        import akshare as ak
        df = ak.stock_profit_sheet_by_report_em(symbol=ak_symbol)
        if df is not None and len(df) > 0:
            data = df.to_dict("records")
            # 清理 NaN 值和日期格式
            for row in data:
                for k, v in list(row.items()):
                    if isinstance(v, float) and math.isnan(v):
                        row[k] = None
                    elif hasattr(v, "strftime"):
                        row[k] = v.strftime("%Y-%m-%d")
            log.info("[%s] 利润表: %d 期", code, len(data))
            return data
    except Exception as e:
        log.warning("[%s] 利润表采集失败: %s", code, e)

    return []


def collect_balance_sheet(code: str, secucode: str = None) -> list[dict]:
    """采集资产负债表（使用akshare获取完整数据）"""
    ak_symbol = _get_ak_symbol(code)

    try:
        import akshare as ak
        df = ak.stock_balance_sheet_by_report_em(symbol=ak_symbol)
        if df is not None and len(df) > 0:
            data = df.to_dict("records")
            # 清理 NaN 值和日期格式
            for row in data:
                for k, v in list(row.items()):
                    if isinstance(v, float) and math.isnan(v):
                        row[k] = None
                    elif hasattr(v, "strftime"):
                        row[k] = v.strftime("%Y-%m-%d")
            log.info("[%s] 资产负债表: %d 期", code, len(data))
            return data
    except Exception as e:
        log.warning("[%s] 资产负债表采集失败: %s", code, e)

    return []


def collect_cash_flow(code: str, secucode: str = None) -> list[dict]:
    """采集现金流量表（使用akshare获取完整数据）"""
    ak_symbol = _get_ak_symbol(code)

    try:
        import akshare as ak
        df = ak.stock_cash_flow_sheet_by_report_em(symbol=ak_symbol)
        if df is not None and len(df) > 0:
            data = df.to_dict("records")
            # 清理 NaN 值和日期格式
            for row in data:
                for k, v in list(row.items()):
                    if isinstance(v, float) and math.isnan(v):
                        row[k] = None
                    elif hasattr(v, "strftime"):
                        row[k] = v.strftime("%Y-%m-%d")
            log.info("[%s] 现金流量表: %d 期", code, len(data))
            return data
    except Exception as e:
        log.warning("[%s] 现金流量表采集失败: %s", code, e)

    return []


def save_main_indicators(db: Session, code: str, data_list: list[dict]) -> int:
    """保存主要指标到数据库"""
    from app.models import FinMainIndicator

    count = 0
    for item in data_list:
        try:
            report_date_str = item.get("REPORT_DATE", "")
            if isinstance(report_date_str, str) and len(report_date_str) >= 10:
                report_date = datetime.strptime(report_date_str[:10], "%Y-%m-%d").date()
            else:
                continue

            report_type_raw = item.get("REPORT_TYPE", "")
            report_type, _ = _parse_report_type(report_type_raw)
            report_name = item.get("REPORT_DATE_NAME", "")

            # 检查是否已存在
            existing = db.query(FinMainIndicator).filter_by(
                stock_code=code,
                report_date=report_date
            ).first()

            if existing:
                # 更新
                existing.raw_json = item
                existing.report_type = report_type
            else:
                # 新增
                indicator = FinMainIndicator(
                    stock_code=code,
                    report_date=report_date,
                    report_type=report_type,
                    raw_json=item,
                )
                db.add(indicator)

            count += 1
        except Exception as e:
            log.warning("[%s] 保存主要指标失败: %s", code, e)

    return count


def save_fin_reports(db: Session, code: str, income_list: list[dict],
                     balance_list: list[dict], cashflow_list: list[dict]) -> int:
    """保存三表数据到 fin_report 表"""
    from app.models import FinReport

    # 按报告期索引数据
    def build_map(data_list):
        m = {}
        for item in data_list:
            date_str = item.get("REPORT_DATE", "")
            if isinstance(date_str, str) and len(date_str) >= 10:
                key = date_str[:10]
            elif hasattr(date_str, "strftime"):
                key = date_str.strftime("%Y-%m-%d")
            else:
                continue
            m[key] = item
        return m

    income_map = build_map(income_list)
    balance_map = build_map(balance_list)
    cashflow_map = build_map(cashflow_list)

    count = 0
    all_dates = set(list(income_map.keys()) + list(balance_map.keys()) + list(cashflow_map.keys()))

    for date_key in all_dates:
        try:
            report_date = datetime.strptime(date_key, "%Y-%m-%d").date()
            income = income_map.get(date_key, {})
            balance = balance_map.get(date_key, {})
            cashflow = cashflow_map.get(date_key, {})

            # 确定报告期名称
            report_name = income.get("REPORT_DATE_NAME") or balance.get("REPORT_DATE_NAME") or date_key
            report_type_raw = income.get("REPORT_TYPE") or balance.get("REPORT_TYPE") or ""
            if "一季" in str(report_type_raw) or "Q1" in str(report_type_raw):
                report_type = "Q1"
            elif "中报" in str(report_type_raw) or "半年" in str(report_type_raw):
                report_type = "H1"
            elif "三季" in str(report_type_raw) or "Q3" in str(report_type_raw):
                report_type = "Q3"
            elif "年报" in str(report_type_raw) or "年度" in str(report_type_raw):
                report_type = "Annual"
            else:
                report_type = "Annual"

            # 公告日期
            notice_date_str = income.get("NOTICE_DATE") or balance.get("NOTICE_DATE") or ""
            notice_date = None
            if isinstance(notice_date_str, str) and len(notice_date_str) >= 10:
                notice_date = datetime.strptime(notice_date_str[:10], "%Y-%m-%d").date()
            elif hasattr(notice_date_str, "strftime"):
                notice_date = notice_date_str.date() if hasattr(notice_date_str, "date") else notice_date_str

            existing = db.query(FinReport).filter_by(
                stock_code=code,
                report_date=report_date
            ).first()

            if existing:
                existing.report_name = report_name
                existing.report_type = report_type
                existing.notice_date = notice_date
                existing.income_json = income
                existing.balance_json = balance
                existing.cashflow_json = cashflow
            else:
                report = FinReport(
                    stock_code=code,
                    report_date=report_date,
                    report_name=report_name,
                    report_type=report_type,
                    notice_date=notice_date,
                    income_json=income,
                    balance_json=balance,
                    cashflow_json=cashflow,
                )
                db.add(report)

            count += 1

        except Exception as e:
            log.warning("[%s] 保存报表失败 %s: %s", code, date_key, e)

    return count


def collect_stock_all_data(code: str, stock_name: str = None) -> dict:
    """采集单只股票的全部财务数据"""
    log.info("[%s] 开始采集全部数据 (东方财富EM Web)", code)

    from app.db import db_session
    from app.models import StockBasic

    result = {
        "main_indicators": 0,
        "fin_reports": 0,
        "stock_basic": False,
    }

    secucode = _get_secucode(code)

    # 1. 保存/更新股票基础信息
    with db_session() as db:
        existing = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
        if not existing:
            basic = StockBasic(
                stock_code=code,
                market=_detect_market(code),
                secucode=secucode,
                stock_name=stock_name or code,
                industry=None,
            )
            db.add(basic)
            result["stock_basic"] = True
            log.info("[%s] 新增股票基础信息", code)
        elif stock_name and existing.stock_name != stock_name:
            existing.stock_name = stock_name
            result["stock_basic"] = True

    # 2. 采集主要指标
    main_data = collect_main_indicators(code, secucode)
    if main_data:
        with db_session() as db:
            result["main_indicators"] = save_main_indicators(db, code, main_data)

    # 3. 采集三表数据
    income_data = collect_income_statement(code, secucode)
    time.sleep(0.5)
    balance_data = collect_balance_sheet(code, secucode)
    time.sleep(0.5)
    cashflow_data = collect_cash_flow(code, secucode)

    if income_data or balance_data or cashflow_data:
        with db_session() as db:
            result["fin_reports"] = save_fin_reports(
                db, code, income_data, balance_data, cashflow_data
            )

    log.info("[%s] 采集完成: 主要指标=%d, 报表=%d", code,
             result["main_indicators"], result["fin_reports"])
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    # 测试采集沃尔核材
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else "002130"
    name = sys.argv[2] if len(sys.argv) > 2 else "沃尔核材"

    result = collect_stock_all_data(code, name)
    print(f"\n采集结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
