"""财务报表API：资产负债表/利润表/现金流量表/主要指标。

单位约定：所有金额字段统一以**元**为单位返回前端，前端FinTable组件自动格式化为万/亿。
比率字段以百分比数值返回（如ROE 15表示15%）。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.db import get_db
from app.core.response import success_response, fail_response
from app.models import FinReport, FinMainIndicator

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])


def _get_reports(db: Session, code: str, report_type: Optional[str], quarters: int):
    """获取最近N期报告（按报告期倒序）。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    query = db.query(FinReport).filter(FinReport.stock_code == code)
    if report_type:
        query = query.filter(FinReport.report_type == report_type)
    return query.order_by(FinReport.report_date.desc()).limit(quarters).all()


def _extract_value(row: dict, *keys, default=None):
    """从原始JSON行中按优先级取字段。"""
    for k in keys:
        v = row.get(k)
        if v is not None and v != "--" and v != "-":
            return v
    return default


def _num(v):
    """将东财值转为数字或None。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if s in ("", "--", "-", "nan", "None"):
        return None
    try:
        if s.endswith("%"):
            return float(s[:-1])
        if s.endswith("亿"):
            return float(s[:-1]) * 1e8
        if s.endswith("万"):
            return float(s[:-1]) * 1e4
        return float(s)
    except (ValueError, TypeError):
        return None


# ===================== 主要指标 =====================

@router.get("/{code}/main-indicators")
def get_main_indicators(
    code: str,
    view: str = Query("report", description="report=按报告期, annual=按年度"),
    quarters: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """主要财务指标（东财主要指标页）。

    主要指标从FinMainIndicator表读取，资产负债数据从FinReport表读取。
    """
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")

    # 获取主要指标
    ind_query = db.query(FinMainIndicator).filter(FinMainIndicator.stock_code == code)
    indicators = ind_query.order_by(FinMainIndicator.report_date.desc()).limit(quarters).all()

    # 获取财务报表数据（用于提取关键指标和资产负债表数据）
    bs_query = db.query(FinReport).filter(FinReport.stock_code == code)
    fin_reports = bs_query.order_by(FinReport.report_date.desc()).limit(quarters).all()
    bs_map = {str(r.report_date): r for r in fin_reports}

    # 如果没有主要指标数据，从FinReport提取列构建
    if not indicators and fin_reports:
        return _build_main_indicators_from_reports(fin_reports, bs_map)

    # 从原始JSON提取数据
    def get_val(raw, key):
        if raw is None:
            return None
        v = raw.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    dates = [str(ind.report_date) for ind in indicators]
    names = [ind.raw_json.get("REPORT_TYPE", "") for ind in indicators]

    def col(key):
        return [get_val(ind.raw_json, key) for ind in indicators]

    def bs_col(key):
        """从资产负债表获取数据"""
        result = []
        for dt in dates:
            r = bs_map.get(dt)
            if r and r.balance_json:
                v = r.balance_json.get(key)
                if v is not None and not (isinstance(v, float) and v != v):  # 排除NaN
                    try:
                        result.append(float(v))
                    except (ValueError, TypeError):
                        result.append(None)
                else:
                    result.append(None)
            else:
                result.append(None)
        return result

    data = {
        "report_dates": dates,
        "report_names": names,
        "sections": [
            {
                "name": "每股指标",
                "items": [
                    {"name": "基本每股收益(元)", "key": "EPSJB", "values": col("EPSJB")},
                    {"name": "每股净资产(元)", "key": "BPS", "values": col("BPS")},
                    {"name": "每股资本公积(元)", "key": "MGZBGJ", "values": col("MGZBGJ")},
                    {"name": "每股未分配利润(元)", "key": "MGWFPLR", "values": col("MGWFPLR")},
                    {"name": "每股经营现金流(元)", "key": "MGJYXJJE", "values": col("MGJYXJJE")},
                ]
            },
            {
                "name": "盈利能力",
                "items": [
                    {"name": "净资产收益率ROE(%)", "key": "ROEJQ", "values": col("ROEJQ")},
                    {"name": "总资产收益率ROA(%)", "key": "ZZCJLL", "values": col("ZZCJLL")},
                    {"name": "销售毛利率(%)", "key": "XSMLL", "values": col("XSMLL")},
                    {"name": "销售净利率(%)", "key": "XSJLL", "values": col("XSJLL")},
                ]
            },
            {
                "name": "成长能力",
                "items": [
                    {"name": "营业总收入同比增长率(%)", "key": "TOTALOPERATEREVETZ", "values": col("TOTALOPERATEREVETZ")},
                    {"name": "归母净利润同比增长率(%)", "key": "PARENTNETPROFITTZ", "values": col("PARENTNETPROFITTZ")},
                    {"name": "扣非净利润同比增长率(%)", "key": "KCFJCXSYJLRTZ", "values": col("KCFJCXSYJLRTZ")},
                ]
            },
            {
                "name": "偿债能力",
                "items": [
                    {"name": "资产负债率(%)", "key": "ZCFZL", "values": col("ZCFZL")},
                    {"name": "流动比率", "key": "LD", "values": col("LD")},
                    {"name": "速动比率", "key": "SD", "values": col("SD")},
                    {"name": "现金流动负债比", "key": "XJLLB", "values": col("XJLLB")},
                ]
            },
            {
                "name": "运营能力",
                "items": [
                    {"name": "总资产周转天数", "key": "ZZCZZTS", "values": col("ZZCZZTS")},
                    {"name": "存货周转天数", "key": "CHZZTS", "values": col("CHZZTS")},
                    {"name": "应收账款周转天数", "key": "YSZKZZTS", "values": col("YSZKZZTS")},
                    {"name": "总资产周转率", "key": "TOAZZL", "values": col("TOAZZL")},
                    {"name": "存货周转率", "key": "CHZZL", "values": col("CHZZL")},
                ]
            },
            {
                "name": "利润表关键科目",
                "items": [
                    {"name": "营业总收入", "key": "TOTALOPERATEREVE", "values": col("TOTALOPERATEREVE")},
                    {"name": "毛利", "key": "MLR", "values": col("MLR")},
                    {"name": "归母净利润", "key": "PARENTNETPROFIT", "values": col("PARENTNETPROFIT")},
                    {"name": "扣非净利润", "key": "KCFJCXSYJLR", "values": col("KCFJCXSYJLR")},
                ]
            },
            {
                "name": "资产负债关键科目",
                "items": [
                    {"name": "总资产", "key": "TOTAL_ASSETS", "values": bs_col("TOTAL_ASSETS")},
                    {"name": "总负债", "key": "TOTAL_LIABILITIES", "values": bs_col("TOTAL_LIABILITIES")},
                    {"name": "股东权益合计", "key": "TOTAL_EQUITY", "values": bs_col("TOTAL_EQUITY")},
                ]
            },
        ]
    }

    return success_response(data)


def _build_main_indicators_from_reports(fin_reports, bs_map):
    """从FinReport提取列构建主要指标数据（当FinMainIndicator无数据时的降级方案）。"""
    dates = [str(r.report_date) for r in fin_reports]
    names = [r.report_name for r in fin_reports]

    def col(field):
        """从FinReport提取列字段"""
        result = []
        for r in fin_reports:
            v = getattr(r, field, None)
            if v is not None:
                try:
                    result.append(float(v))
                except (ValueError, TypeError):
                    result.append(None)
            else:
                result.append(None)
        return result

    def bs_col(key):
        """从资产负债表JSON获取数据"""
        result = []
        for dt in dates:
            r = bs_map.get(dt)
            if r and r.balance_json:
                v = r.balance_json.get(key)
                if v is not None and not (isinstance(v, float) and v != v):
                    try:
                        result.append(float(v))
                    except (ValueError, TypeError):
                        result.append(None)
                else:
                    result.append(None)
            else:
                result.append(None)
        return result

    def inc_col(key):
        """从利润表JSON获取数据"""
        result = []
        for r in fin_reports:
            if r.income_json:
                v = r.income_json.get(key)
                if v is not None and not (isinstance(v, float) and v != v):
                    try:
                        result.append(float(v))
                    except (ValueError, TypeError):
                        result.append(None)
                else:
                    result.append(None)
            else:
                result.append(None)
        return result

    # 计算每股指标需要的总股本
    share_capital_list = bs_col("SHARE_CAPITAL")

    def calc_per_share(total_field):
        """计算每股数据"""
        result = []
        for i, r in enumerate(fin_reports):
            total_val = getattr(r, total_field, None)
            sc = share_capital_list[i] if i < len(share_capital_list) else None
            if total_val is not None and sc and sc > 0:
                try:
                    result.append(round(float(total_val) / sc, 4))
                except (ValueError, TypeError, ZeroDivisionError):
                    result.append(None)
            else:
                result.append(None)
        return result

    data = {
        "report_dates": dates,
        "report_names": names,
        "sections": [
            {
                "name": "每股指标",
                "items": [
                    {"name": "基本每股收益(元)", "key": "EPSJB", "values": calc_per_share("net_profit_parent")},
                    {"name": "每股净资产(元)", "key": "BPS", "values": calc_per_share("total_equity")},
                    {"name": "每股经营现金流(元)", "key": "MGJYXJJE", "values": calc_per_share("operate_cash_net")},
                ]
            },
            {
                "name": "盈利能力",
                "items": [
                    {"name": "净资产收益率ROE(%)", "key": "ROEJQ", "values": col("roe")},
                    {"name": "总资产收益率ROA(%)", "key": "ZZCJLL", "values": col("roa")},
                    {"name": "销售毛利率(%)", "key": "XSMLL", "values": col("gross_margin")},
                    {"name": "销售净利率(%)", "key": "XSJLL", "values": col("net_margin")},
                ]
            },
            {
                "name": "成长能力",
                "items": [
                    {"name": "营业总收入同比增长率(%)", "key": "TOTALOPERATEREVETZ", "values": col("revenue_yoy")},
                    {"name": "归母净利润同比增长率(%)", "key": "PARENTNETPROFITTZ", "values": col("net_profit_yoy")},
                    {"name": "总资产同比增长率(%)", "key": "TOTALASY", "values": col("assets_yoy")},
                ]
            },
            {
                "name": "偿债能力",
                "items": [
                    {"name": "资产负债率(%)", "key": "ZCFZL", "values": col("debt_ratio")},
                    {"name": "流动比率", "key": "LD", "values": col("current_ratio")},
                    {"name": "速动比率", "key": "SD", "values": col("quick_ratio")},
                ]
            },
            {
                "name": "利润表关键科目",
                "items": [
                    {"name": "营业总收入", "key": "TOTALOPERATEREVE", "values": col("total_revenue")},
                    {"name": "营业利润", "key": "OPERATEPROFIT", "values": col("operate_profit")},
                    {"name": "利润总额", "key": "TOTALPROFIT", "values": col("total_profit")},
                    {"name": "归母净利润", "key": "PARENTNETPROFIT", "values": col("net_profit_parent")},
                    {"name": "扣非净利润", "key": "KCFJCXSYJLR", "values": col("deduct_net_profit")},
                ]
            },
            {
                "name": "资产负债关键科目",
                "items": [
                    {"name": "总资产", "key": "TOTAL_ASSETS", "values": col("total_assets")},
                    {"name": "总负债", "key": "TOTAL_LIABILITIES", "values": col("total_liabilities")},
                    {"name": "股东权益合计", "key": "TOTAL_EQUITY", "values": col("total_equity")},
                ]
            },
            {
                "name": "现金流量关键科目",
                "items": [
                    {"name": "经营活动现金流净额", "key": "OPERATECASHNET", "values": col("operate_cash_net")},
                ]
            },
        ]
    }
    return success_response(data)


def _calc_cash_ps(r: FinReport):
    if r.operate_cash_net is None:
        return None
    bj = r.balance_json or {}
    share_capital = bj.get("SHARE_CAPITAL")
    if share_capital:
        try:
            sc = float(share_capital)
            if sc > 0:
                return round(float(r.operate_cash_net) / sc, 4)
        except (ValueError, TypeError):
            pass
    return None

BS_GROUPS = [
    {
        "name": "流动资产",
        "fields": [
            ("货币资金", ["MONETARYFUNDS"]),
            ("交易性金融资产", ["TRADE_FINASSET_NOTFVTPL", "TRADE_FINASSET", "FVTPL_FINASSET", "TRADE_FINANCIAL_ASSET"]),
            ("应收票据", ["NOTE_RECE", "BILL_RECE"]),
            ("应收账款", ["ACCOUNTS_RECE"]),
            ("应收票据及应收账款", ["NOTE_ACCOUNTS_RECE", "ACCOUNTS_RECE", "NOTE_RECE"]),
            ("预付款项", ["PREPAYMENT", "ADVANCE_PAYMENT"]),
            ("其他应收款", ["OTHER_RECE", "OTHER_RECEIVABLE"]),
            ("其他应收款合计", ["TOTAL_OTHER_RECE", "OTHER_RECE"]),
            ("存货", ["INVENTORY"]),
            ("合同资产", ["CONTRACT_ASSET"]),
            ("一年内到期的非流动资产", ["NONCURRENT_ASSET_1YEAR", "NON_CURRENT_ASSET_1Y"]),
            ("其他流动资产", ["OTHER_CURRENT_ASSET"]),
            ("流动资产合计", ["TOTAL_CURRENT_ASSETS"]),
        ]
    },
    {
        "name": "非流动资产",
        "fields": [
            ("可供出售金融资产", ["AVAILABLE_SALE_FINASSET", "AVAIL_SALE_FIN"]),
            ("持有至到期投资", ["HOLD_MATURITY_INVEST"]),
            ("长期应收款", ["LONG_RECE", "LONG_TERM_RECE"]),
            ("长期股权投资", ["LONG_EQUITY_INVEST", "LONG_EQ_INVEST"]),
            ("投资性房地产", ["INVEST_REALESTATE"]),
            ("固定资产", ["FIXED_ASSET"]),
            ("在建工程", ["CIP", "CONSTRUCTION_IN_PROGRESS"]),
            ("生产性生物资产", ["PRODUCTIVE_BIOLOGY_ASSET"]),
            ("油气资产", ["OIL_GAS_ASSET"]),
            ("无形资产", ["INTANGIBLE_ASSET"]),
            ("开发支出", ["DEVELOP_EXPENSE"]),
            ("商誉", ["GOODWILL"]),
            ("长期待摊费用", ["LONG_PREPAID_EXPENSE"]),
            ("递延所得税资产", ["DEFER_TAX_ASSET"]),
            ("其他非流动资产", ["OTHER_NONCURRENT_ASSET"]),
            ("非流动资产合计", ["TOTAL_NONCURRENT_ASSETS"]),
            ("资产总计", ["TOTAL_ASSETS"]),
        ]
    },
    {
        "name": "流动负债",
        "fields": [
            ("短期借款", ["SHORT_LOAN"]),
            ("交易性金融负债", ["FVTPL_FINLIAB", "TRADE_FINANCIAL_LIAB"]),
            ("应付票据", ["NOTE_PAYABLE", "BILL_PAYABLE"]),
            ("应付账款", ["ACCOUNTS_PAYABLE"]),
            ("应付票据及应付账款", ["NOTE_ACCOUNTS_PAYABLE", "ACCOUNTS_PAYABLE"]),
            ("预收款项", ["ADVANCE_RECEIVABLES"]),
            ("合同负债", ["CONTRACT_LIAB"]),
            ("应付职工薪酬", ["STAFF_SALARY_PAYABLE", "EMPLOYEE_PAYABLE"]),
            ("应交税费", ["TAX_PAYABLE"]),
            ("其他应付款", ["OTHER_PAYABLE"]),
            ("其他应付款合计", ["TOTAL_OTHER_PAYABLE", "OTHER_PAYABLE"]),
            ("一年内到期的非流动负债", ["NONCURRENT_LIAB_1YEAR"]),
            ("其他流动负债", ["OTHER_CURRENT_LIAB"]),
            ("流动负债合计", ["TOTAL_CURRENT_LIAB"]),
        ]
    },
    {
        "name": "非流动负债",
        "fields": [
            ("长期借款", ["LONG_LOAN"]),
            ("应付债券", ["BOND_PAYABLE"]),
            ("长期应付款", ["LONG_PAYABLE"]),
            ("递延所得税负债", ["DEFER_TAX_LIAB"]),
            ("其他非流动负债", ["OTHER_NONCURRENT_LIAB"]),
            ("非流动负债合计", ["TOTAL_NONCURRENT_LIAB"]),
            ("负债合计", ["TOTAL_LIABILITIES", "TOTAL_LIAB"]),
        ]
    },
    {
        "name": "所有者权益",
        "fields": [
            ("股本", ["SHARE_CAPITAL", "CAPITAL_STOCK"]),
            ("资本公积", ["CAPITAL_RESERVE"]),
            ("盈余公积", ["SURPLUS_RESERVE"]),
            ("未分配利润", ["UNASSIGN_RPOFIT", "UNALLOCATED_PROFIT"]),
            ("其他综合收益", ["OTHER_COMPRE_INCOME"]),
            ("归属于母公司股东权益合计", ["TOTAL_PARENT_EQUITY"]),
            ("少数股东权益", ["MINORITY_EQUITY"]),
            ("股东权益合计", ["TOTAL_EQUITY"]),
            ("负债和股东权益合计", ["TOTAL_LIAB_EQUITY", "TOTAL_ASSETS"]),
        ]
    },
]


@router.get("/{code}/balance-sheet")
def get_balance_sheet(
    code: str,
    view: str = Query("report", description="report=按报告期"),
    quarters: int = Query(8, ge=1, le=20),
    report_type: Optional[str] = Query(None, description="Q1/H1/Q3/Annual"),
    db: Session = Depends(get_db),
):
    """资产负债表。金额单位：元。"""
    return _build_report_table(db, code, quarters, report_type, "balance_json", BS_GROUPS)


# ===================== 利润表 =====================

IS_GROUPS = [
    {
        "name": "利润表",
        "fields": [
            ("营业总收入", ["TOTAL_OPERATE_INCOME"]),
            ("营业收入", ["OPERATE_INCOME"]),
            ("营业总成本", ["TOTAL_OPERATE_COST"]),
            ("营业成本", ["OPERATE_COST"]),
            ("税金及附加", ["OPERATE_TAX_ADD"]),
            ("销售费用", ["SALE_EXPENSE"]),
            ("管理费用", ["MANAGE_EXPENSE"]),
            ("研发费用", ["RESEARCH_EXPENSE", "ME_RESEARCH_EXPENSE"]),
            ("财务费用", ["FINANCE_EXPENSE"]),
            ("其中:利息费用", ["FE_INTEREST_EXPENSE"]),
            ("利息收入", ["FE_INTEREST_INCOME"]),
            ("资产减值损失", ["ASSET_IMPAIRMENT_LOSS"]),
            ("信用减值损失", ["CREDIT_IMPAIRMENT_LOSS"]),
            ("公允价值变动收益", ["FAIRVALUE_CHANGE_INCOME"]),
            ("投资收益", ["INVEST_INCOME"]),
            ("资产处置收益", ["ASSET_DISPOSAL_INCOME"]),
            ("其他收益", ["OTHER_INCOME"]),
            ("营业利润", ["OPERATE_PROFIT"]),
            ("利润总额", ["TOTAL_PROFIT"]),
            ("净利润", ["NETPROFIT"]),
            ("归属于母公司所有者的净利润", ["PARENT_NETPROFIT"]),
            ("少数股东损益", ["MINORITY_INTEREST"]),
            ("扣除非经常性损益后的净利润", ["DEDUCT_PARENT_NETPROFIT"]),
            ("基本每股收益(元)", ["BASIC_EPS"]),
            ("稀释每股收益(元)", ["DILUTED_EPS"]),
        ]
    },
]


@router.get("/{code}/income-statement")
def get_income_statement(
    code: str,
    view: str = Query("report", description="report=按报告期"),
    quarters: int = Query(8, ge=1, le=20),
    report_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """利润表。金额单位：元，EPS为元/股。"""
    return _build_report_table(db, code, quarters, report_type, "income_json", IS_GROUPS)


# ===================== 现金流量表 =====================

CF_GROUPS = [
    {
        "name": "经营活动产生的现金流量",
        "fields": [
            ("销售商品、提供劳务收到的现金", ["SALES_SERVICES"]),
            ("收到的税费返还", ["RECEIVE_TAX_REFUND"]),
            ("收到其他与经营活动有关的现金", ["RECEIVE_OTHER_OPERATE"]),
            ("经营活动现金流入小计", ["TOTAL_OPERATE_INFLOW"]),
            ("购买商品、接受劳务支付的现金", ["BUY_SERVICES"]),
            ("支付给职工以及为职工支付的现金", ["PAY_STAFF_CASH"]),
            ("支付的各项税费", ["PAY_ALL_TAX"]),
            ("支付其他与经营活动有关的现金", ["PAY_OTHER_OPERATE"]),
            ("经营活动现金流出小计", ["TOTAL_OPERATE_OUTFLOW"]),
            ("经营活动产生的现金流量净额", ["NETCASH_OPERATE"]),
        ]
    },
    {
        "name": "投资活动产生的现金流量",
        "fields": [
            ("收回投资收到的现金", ["WITHDRAW_INVEST"]),
            ("取得投资收益收到的现金", ["RECEIVE_INVEST_INCOME"]),
            ("处置固定资产、无形资产和其他长期资产收回的现金净额", ["DISPOSAL_LONG_ASSET"]),
            ("收到其他与投资活动有关的现金", ["RECEIVE_OTHER_INVEST"]),
            ("投资活动现金流入小计", ["TOTAL_INVEST_INFLOW"]),
            ("购建固定资产、无形资产和其他长期资产支付的现金", ["CONSTRUCT_LONG_ASSET"]),
            ("投资支付的现金", ["INVEST_PAY_CASH"]),
            ("支付其他与投资活动有关的现金", ["PAY_OTHER_INVEST"]),
            ("投资活动现金流出小计", ["TOTAL_INVEST_OUTFLOW"]),
            ("投资活动产生的现金流量净额", ["NETCASH_INVEST"]),
        ]
    },
    {
        "name": "筹资活动产生的现金流量",
        "fields": [
            ("吸收投资收到的现金", ["ACCEPT_INVEST_CASH"]),
            ("取得借款收到的现金", ["RECEIVE_LOAN_CASH"]),
            ("发行债券收到的现金", ["ISSUE_BOND"]),
            ("收到其他与筹资活动有关的现金", ["RECEIVE_OTHER_FINANCE"]),
            ("筹资活动现金流入小计", ["TOTAL_FINANCE_INFLOW"]),
            ("偿还债务支付的现金", ["PAY_DEBT_CASH"]),
            ("分配股利、利润或偿付利息支付的现金", ["ASSIGN_DIVIDEND_PORFIT"]),
            ("支付其他与筹资活动有关的现金", ["PAY_OTHER_FINANCE"]),
            ("筹资活动现金流出小计", ["TOTAL_FINANCE_OUTFLOW"]),
            ("筹资活动产生的现金流量净额", ["NETCASH_FINANCE"]),
        ]
    },
    {
        "name": "现金及现金等价物",
        "fields": [
            ("汇率变动对现金及现金等价物的影响", ["RATE_CHANGE_EFFECT"]),
            ("现金及现金等价物净增加额", ["CCE_ADD"]),
            ("期初现金及现金等价物余额", ["BEGIN_CCE"]),
            ("期末现金及现金等价物余额", ["END_CCE"]),
        ]
    },
]


@router.get("/{code}/cash-flow")
def get_cash_flow(
    code: str,
    view: str = Query("report", description="report=按报告期"),
    quarters: int = Query(8, ge=1, le=20),
    report_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """现金流量表。金额单位：元。"""
    return _build_report_table(db, code, quarters, report_type, "cashflow_json", CF_GROUPS)


# ===================== 核心构建函数 =====================

def _build_report_table(
    db: Session, code: str, quarters: int, report_type: Optional[str],
    json_field: str, groups: list,
):
    """通用三表构建函数：从JSON原始数据中提取科目，按东方财富F10格式返回。

    金额单位：保持元为单位，EPS等每股指标保持原始单位。
    """
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    query = db.query(FinReport).filter(FinReport.stock_code == code)
    if report_type:
        query = query.filter(FinReport.report_type == report_type)
    reports = query.order_by(FinReport.report_date.desc()).limit(quarters).all()
    if not reports:
        return success_response({
            "report_dates": [],
            "report_names": [],
            "sections": []
        })

    date_to_report = {str(r.report_date): r for r in reports}
    dates = [str(r.report_date) for r in reports]
    names = [r.report_name for r in reports]

    eps_keys = {"BASIC_EPS", "DILUTED_EPS"}

    result_sections = []
    for group in groups:
        items = []
        for label, keys in group["fields"]:
            if isinstance(keys, str):
                keys = [keys]
            values = []
            for i, dt in enumerate(dates):
                r = date_to_report.get(dt)
                if not r:
                    values.append(None)
                    continue
                raw = getattr(r, json_field) or {}
                val = None
                for key in keys:
                    val = _em_value(raw, key, is_eps=(key in eps_keys))
                    if val is not None:
                        break
                values.append(val)
            items.append({"name": label, "key": keys[0] or f"row_{len(items)}", "values": values})
        result_sections.append({"name": group["name"], "items": items})

    return success_response({
        "report_dates": dates,
        "report_names": names,
        "sections": result_sections,
    })


def _em_value(raw: dict, key: str, is_eps: bool = False):
    """从东方财富原始数据中提取值，返回数字或None。

    金额单位：元（东财原始就是元，不转换）。
    """
    if not key:
        return None
    v = raw.get(key)
    if v is None:
        return None
    # 处理 nan/inf 值
    if isinstance(v, float) and (v != v or v == float('inf') or v == float('-inf')):
        return None
    if isinstance(v, (int, float)):
        return float(v) if not is_eps else round(float(v), 4)
    s = str(v).strip().replace(",", "")
    if s in ("", "--", "-", "nan", "NaN", "None"):
        return None
    try:
        fv = float(s)
        if fv != fv or fv == float('inf') or fv == float('-inf'):
            return None
        return fv if not is_eps else round(fv, 4)
    except (ValueError, TypeError):
        return None


# ===================== 杜邦分析 =====================

@router.get("/{code}/dupont")
def get_dupont_analysis(
    code: str,
    quarters: int = Query(6, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """杜邦分析树形结构数据。

    树形结构：ROE = 销售净利率 × 总资产周转率 × 权益乘数
    每个节点包含: name(名称)、value(当前值)、unit(单位)、formula(公式)、
                  history(近N期值数组)、yoy(同比变化)、children(子节点)
    """
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")

    # 获取资产负债表和利润表数据
    reports = db.query(FinReport).filter(
        FinReport.stock_code == code
    ).order_by(FinReport.report_date.desc()).limit(quarters).all()

    if not reports:
        return success_response({
            "report_dates": [],
            "nodes": []
        })

    dates = [str(r.report_date) for r in reports]

    def gv(raw, *keys):
        """从JSON中按优先级取值"""
        if not raw:
            return None
        for k in keys:
            v = _em_value(raw, k)
            if v is not None:
                return v
        return None

    def to_pct(v, decimals=2):
        """转为百分比"""
        if v is None:
            return None
        return round(v * 100, decimals)

    def build_node(name, key, current, history, unit, formula="", children=None, is_pct=False):
        """构建一个节点"""
        yoy = None
        if len(history) >= 2 and history[-2] not in (None, 0):
            yoy = round((history[-1] - history[-2]) / abs(history[-2]) * 100, 2)
        return {
            "name": name,
            "key": key,
            "value": current,
            "history": history,
            "yoy": yoy,
            "unit": unit,
            "formula": formula,
            "is_pct": is_pct,
            "children": children or []
        }

    # 按时间正序计算（早→晚）
    reports_asc = list(reversed(reports))
    bs_list = [r.balance_json or {} for r in reports_asc]
    is_list = [r.income_json or {} for r in reports_asc]

    n = len(reports_asc)
    # 各指标历史值
    rev_list = [gv(is_, "OPERATE_INCOME", "TOTAL_OPERATE_INCOME") for is_ in is_list]
    cost_list = [gv(is_, "OPERATE_COST") for is_ in is_list]
    np_list = [gv(is_, "PARENT_NETPROFIT", "NETPROFIT") for is_ in is_list]
    total_np_list = [gv(is_, "NETPROFIT") for is_ in is_list]
    sale_exp_list = [gv(is_, "SALE_EXPENSE") for is_ in is_list]
    manage_exp_list = [gv(is_, "MANAGE_EXPENSE") for is_ in is_list]
    rd_exp_list = [gv(is_, "RESEARCH_EXPENSE", "ME_RESEARCH_EXPENSE") for is_ in is_list]
    fin_exp_list = [gv(is_, "FINANCE_EXPENSE") for is_ in is_list]
    tax_list = [gv(is_, "OPERATE_TAX_ADD") for is_ in is_list]
    income_tax_list = [gv(is_, "INCOME_TAX", "INCOME_TAX_EXPENSE") for is_ in is_list]
    total_profit_list = [gv(is_, "TOTAL_PROFIT") for is_ in is_list]

    # 资产负债表字段
    total_assets_list = [gv(bs, "TOTAL_ASSETS") for bs in bs_list]
    total_liab_list = [gv(bs, "TOTAL_LIABILITIES", "TOTAL_LIAB") for bs in bs_list]
    total_equity_list = [gv(bs, "TOTAL_EQUITY") for bs in bs_list]
    current_assets_list = [gv(bs, "TOTAL_CURRENT_ASSETS") for bs in bs_list]
    noncurrent_assets_list = [gv(bs, "TOTAL_NONCURRENT_ASSETS") for bs in bs_list]
    current_liab_list = [gv(bs, "TOTAL_CURRENT_LIAB") for bs in bs_list]
    inventory_list = [gv(bs, "INVENTORY") for bs in bs_list]
    ar_list = [gv(bs, "ACCOUNTS_RECE", "ACCOUNTS_RECEIVABLE") for bs in bs_list]

    def safe_ratio(num, den, pct=True):
        if num is None or den is None or den == 0:
            return None
        v = num / den
        return v * 100 if pct else v

    def safe_diff(a, b, pct=True):
        if a is None or b is None:
            return None
        v = a - b
        return v * 100 if pct else v

    # 各级指标历史
    def make_history(pct, *lists):
        """根据多个等长列表逐项计算比值。pct: 是否转百分比"""
        result = []
        for items in zip(*lists):
            args = list(items) + [pct]
            result.append(safe_ratio(*args))
        return result

    # 顶层：ROE（净资产收益率，单位%）
    roe_hist = make_history(True, np_list, total_equity_list)
    # 销售净利率（%）
    npm_hist = make_history(True, np_list, rev_list)
    # 总资产周转率（次），不*100
    tat_hist = make_history(False, rev_list, total_assets_list)
    # 权益乘数（倍），不*100
    em_hist = make_history(False, total_assets_list, total_equity_list)

    # 销售净利率拆解
    gpm_hist = make_history(True, [r - c if r and c else None for r, c in zip(rev_list, cost_list)], rev_list)
    sale_rate_hist = make_history(True, sale_exp_list, rev_list)
    manage_rate_hist = make_history(True, manage_exp_list, rev_list)
    rd_rate_hist = make_history(True, rd_exp_list, rev_list)
    fin_rate_hist = make_history(True, fin_exp_list, rev_list)
    tax_rate_hist = make_history(True, income_tax_list, total_profit_list)

    # 总资产周转率拆解
    cat_hist = make_history(False, rev_list, current_assets_list)
    ncat_hist = make_history(False, rev_list, noncurrent_assets_list)

    # 权益乘数拆解
    dr_hist = make_history(True, total_liab_list, total_assets_list)

    # 资产侧
    inv_turnover_hist = make_history(False, cost_list, inventory_list)
    ar_turnover_hist = make_history(False, rev_list, ar_list)
    cash_hist = [gv(bs, "MONETARYFUNDS") for bs in bs_list]
    cash_rate_hist = make_history(True, cash_hist, total_assets_list)

    # 取最新值
    def last(h):
        return h[-1] if h else None

    # 构建子节点
    npm_children = [
        build_node("毛利率", "gross_margin", last(gpm_hist), gpm_hist, "%",
                   "(营业收入-营业成本)/营业收入", is_pct=True),
        build_node("销售费用率", "sale_rate", last(sale_rate_hist), sale_rate_hist, "%",
                   "销售费用/营业收入", is_pct=True),
        build_node("管理费用率", "manage_rate", last(manage_rate_hist), manage_rate_hist, "%",
                   "管理费用/营业收入", is_pct=True),
        build_node("研发费用率", "rd_rate", last(rd_rate_hist), rd_rate_hist, "%",
                   "研发费用/营业收入", is_pct=True),
        build_node("财务费用率", "fin_rate", last(fin_rate_hist), fin_rate_hist, "%",
                   "财务费用/营业收入", is_pct=True),
        build_node("实际所得税率", "tax_rate", last(tax_rate_hist), tax_rate_hist, "%",
                   "所得税/利润总额", is_pct=True),
    ]

    tat_children = [
        build_node("流动资产周转率", "current_at", last(cat_hist), cat_hist, "次",
                   "营业收入/流动资产"),
        build_node("非流动资产周转率", "noncurrent_at", last(ncat_hist), ncat_hist, "次",
                   "营业收入/非流动资产"),
    ]

    em_children = [
        build_node("资产负债率", "debt_ratio", last(dr_hist), dr_hist, "%",
                   "总负债/总资产", is_pct=True),
        build_node("1-资产负债率", "one_minus_dr",
                   round(100 - last(dr_hist), 2) if last(dr_hist) is not None else None,
                   [round(100 - v, 2) if v is not None else None for v in dr_hist], "%",
                   "1-资产负债率", is_pct=True),
    ]

    # 顶部ROE节点
    roe_node = build_node(
        "ROE 净资产收益率", "roe", last(roe_hist), roe_hist, "%",
        "销售净利率 × 总资产周转率 × 权益乘数",
        children=[
            build_node("销售净利率", "net_margin", last(npm_hist), npm_hist, "%",
                       "净利润/营业收入", npm_children, is_pct=True),
            build_node("总资产周转率", "asset_turnover", last(tat_hist), tat_hist, "次",
                       "营业收入/总资产", tat_children),
            build_node("权益乘数", "equity_multiplier", last(em_hist), em_hist, "倍",
                       "总资产/股东权益", em_children),
        ],
        is_pct=True
    )

    # 资产质量节点
    asset_quality = build_node(
        "资产质量", "asset_quality", None, [], "",
        "辅助分析",
        children=[
            build_node("存货周转率", "inv_turnover", last(inv_turnover_hist),
                       inv_turnover_hist, "次", "营业成本/存货"),
            build_node("应收账款周转率", "ar_turnover", last(ar_turnover_hist),
                       ar_turnover_hist, "次", "营业收入/应收账款"),
            build_node("货币资金占总资产比", "cash_rate", last(cash_rate_hist),
                       cash_rate_hist, "%", "货币资金/总资产", is_pct=True),
        ]
    )

    return success_response({
        "report_dates": dates,
        "report_names": [r.report_name for r in reports],
        "nodes": [roe_node, asset_quality]
    })
