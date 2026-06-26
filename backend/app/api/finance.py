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

    从FinMainIndicator表读取原始JSON数据，按东财格式组织返回。
    """
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    query = db.query(FinMainIndicator).filter(FinMainIndicator.stock_code == code)
    indicators = query.order_by(FinMainIndicator.report_date.desc()).limit(quarters).all()

    if not indicators:
        return success_response({
            "report_dates": [],
            "report_names": [],
            "sections": []
        })

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
                    {"name": "总资产", "key": "TOTAL_ASSETS", "values": col("TOTAL_ASSETS")},
                    {"name": "总负债", "key": "TOTAL_LIABILITIES", "values": col("TOTAL_LIABILITIES")},
                    {"name": "股东权益合计", "key": "TOTAL_EQUITY", "values": col("TOTAL_EQUITY")},
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


# ===================== 资产负债表 =====================

BS_GROUPS = [
    {
        "name": "流动资产",
        "fields": [
            ("货币资金", "MONETARYFUNDS"),
            ("交易性金融资产", "FVTPL_FINASSET"),
            ("应收票据及应收账款", "NOTE_ACCOUNTS_RECE"),
            ("应收账款", "ACCOUNTS_RECE"),
            ("预付款项", "PREPAYMENT"),
            ("其他应收款合计", "TOTAL_OTHER_RECE"),
            ("存货", "INVENTORY"),
            ("合同资产", "CONTRACT_ASSET"),
            ("一年内到期的非流动资产", "NONCURRENT_ASSET_1YEAR"),
            ("其他流动资产", "OTHER_CURRENT_ASSET"),
            ("流动资产合计", "TOTAL_CURRENT_ASSETS"),
        ]
    },
    {
        "name": "非流动资产",
        "fields": [
            ("可供出售金融资产", "AVAILABLE_SALE_FINASSET"),
            ("持有至到期投资", "HOLD_MATURITY_INVEST"),
            ("长期应收款", "LONG_RECE"),
            ("长期股权投资", "LONG_EQUITY_INVEST"),
            ("投资性房地产", "INVEST_REALESTATE"),
            ("固定资产", "FIXED_ASSET"),
            ("在建工程", "CIP"),
            ("生产性生物资产", "PRODUCTIVE_BIOLOGY_ASSET"),
            ("油气资产", "OIL_GAS_ASSET"),
            ("无形资产", "INTANGIBLE_ASSET"),
            ("开发支出", "DEVELOP_EXPENSE"),
            ("商誉", "GOODWILL"),
            ("长期待摊费用", "LONG_PREPAID_EXPENSE"),
            ("递延所得税资产", "DEFER_TAX_ASSET"),
            ("其他非流动资产", "OTHER_NONCURRENT_ASSET"),
            ("非流动资产合计", "TOTAL_NONCURRENT_ASSETS"),
        ]
    },
    {
        "name": "资产总计",
        "fields": [
            ("资产总计", "TOTAL_ASSETS"),
        ]
    },
    {
        "name": "流动负债",
        "fields": [
            ("短期借款", "SHORT_LOAN"),
            ("交易性金融负债", "FVTPL_FINLIAB"),
            ("应付票据及应付账款", "NOTE_ACCOUNTS_PAYABLE"),
            ("应付账款", "ACCOUNTS_PAYABLE"),
            ("预收款项", "ADVANCE_RECEIVABLES"),
            ("合同负债", "CONTRACT_LIAB"),
            ("应付职工薪酬", "STAFF_SALARY_PAYABLE"),
            ("应交税费", "TAX_PAYABLE"),
            ("其他应付款合计", "TOTAL_OTHER_PAYABLE"),
            ("一年内到期的非流动负债", "NONCURRENT_LIAB_1YEAR"),
            ("其他流动负债", "OTHER_CURRENT_LIAB"),
            ("流动负债合计", "TOTAL_CURRENT_LIAB"),
        ]
    },
    {
        "name": "非流动负债",
        "fields": [
            ("长期借款", "LONG_LOAN"),
            ("应付债券", "BOND_PAYABLE"),
            ("长期应付款", "LONG_PAYABLE"),
            ("递延所得税负债", "DEFER_TAX_LIAB"),
            ("其他非流动负债", "OTHER_NONCURRENT_LIAB"),
            ("非流动负债合计", "TOTAL_NONCURRENT_LIAB"),
        ]
    },
    {
        "name": "负债合计",
        "fields": [
            ("负债合计", "TOTAL_LIABILITIES"),
        ]
    },
    {
        "name": "所有者权益",
        "fields": [
            ("股本", "SHARE_CAPITAL"),
            ("资本公积", "CAPITAL_RESERVE"),
            ("盈余公积", "SURPLUS_RESERVE"),
            ("未分配利润", "UNASSIGN_RPOFIT"),
            ("其他综合收益", "OTHER_COMPRE_INCOME"),
            ("归属于母公司股东权益合计", "TOTAL_PARENT_EQUITY"),
            ("少数股东权益", "MINORITY_EQUITY"),
            ("股东权益合计", "TOTAL_EQUITY"),
            ("负债和股东权益合计", "TOTAL_LIAB_EQUITY"),
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
            ("营业总收入", "TOTAL_OPERATE_INCOME"),
            ("营业收入", "OPERATE_INCOME"),
            ("营业总成本", "TOTAL_OPERATE_COST"),
            ("营业成本", "OPERATE_COST"),
            ("税金及附加", "OPERATE_TAX_ADD"),
            ("销售费用", "SALE_EXPENSE"),
            ("管理费用", "MANAGE_EXPENSE"),
            ("研发费用", "RESEARCH_EXPENSE"),
            ("财务费用", "FINANCE_EXPENSE"),
            ("其中:利息费用", "FE_INTEREST_EXPENSE"),
            ("利息收入", "FE_INTEREST_INCOME"),
            ("资产减值损失", "ASSET_IMPAIRMENT_LOSS"),
            ("信用减值损失", "CREDIT_IMPAIRMENT_LOSS"),
            ("公允价值变动收益", "FAIRVALUE_CHANGE_INCOME"),
            ("投资收益", "INVEST_INCOME"),
            ("资产处置收益", "ASSET_DISPOSAL_INCOME"),
            ("其他收益", "OTHER_INCOME"),
            ("营业利润", "OPERATE_PROFIT"),
            ("利润总额", "TOTAL_PROFIT"),
            ("净利润", "NETPROFIT"),
            ("归属于母公司所有者的净利润", "PARENT_NETPROFIT"),
            ("少数股东损益", "MINORITY_INTEREST"),
            ("扣除非经常性损益后的净利润", "DEDUCT_PARENT_NETPROFIT"),
            ("基本每股收益(元)", "BASIC_EPS"),
            ("稀释每股收益(元)", "DILUTED_EPS"),
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
            ("销售商品、提供劳务收到的现金", "SALES_SERVICES"),
            ("收到的税费返还", "TAX_RECEIVE"),
            ("收到其他与经营活动有关的现金", "OTHER_OPERATE_IN"),
            ("经营活动现金流入小计", "TOTAL_OPERATE_IN"),
            ("购买商品、接受劳务支付的现金", "BUY_SERVICES"),
            ("支付给职工以及为职工支付的现金", "STAFF_PAY"),
            ("支付的各项税费", "TAX_PAY"),
            ("支付其他与经营活动有关的现金", "OTHER_OPERATE_OUT"),
            ("经营活动现金流出小计", "TOTAL_OPERATE_OUT"),
            ("经营活动产生的现金流量净额", "NETCASH_OPERATE"),
        ]
    },
    {
        "name": "投资活动产生的现金流量",
        "fields": [
            ("收回投资收到的现金", "WITHDRAW_INVEST"),
            ("取得投资收益收到的现金", "INVEST_INCOME_RECE"),
            ("处置固定资产、无形资产和其他长期资产收回的现金净额", "DISPOSAL_LONG_ASSET"),
            ("投资活动现金流入小计", "TOTAL_INVEST_IN"),
            ("购建固定资产、无形资产和其他长期资产支付的现金", "CONSTRUCT_LONG_ASSET"),
            ("投资支付的现金", "INVEST_PAY"),
            ("投资活动现金流出小计", "TOTAL_INVEST_OUT"),
            ("投资活动产生的现金流量净额", "NETCASH_INVEST"),
        ]
    },
    {
        "name": "筹资活动产生的现金流量",
        "fields": [
            ("取得借款收到的现金", "RECEIVE_LOAN"),
            ("筹资活动现金流入小计", "TOTAL_FINANCE_IN"),
            ("偿还债务支付的现金", "PAY_DEBT"),
            ("分配股利、利润或偿付利息支付的现金", "ASSIGN_DIVIDEND_PORFIT"),
            ("筹资活动现金流出小计", "TOTAL_FINANCE_OUT"),
            ("筹资活动产生的现金流量净额", "NETCASH_FINANCE"),
        ]
    },
    {
        "name": "现金及现金等价物",
        "fields": [
            ("汇率变动对现金及现金等价物的影响", "RATE_CHANGE_EFFECT"),
            ("现金及现金等价物净增加额", "NETCASH_INCREASE"),
            ("期初现金及现金等价物余额", "BEGIN_CCE"),
            ("期末现金及现金等价物余额", "END_CCE"),
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

    # EPS字段名集合，这些不需要除以万元
    eps_keys = {"BASIC_EPS", "DILUTED_EPS"}

    result_sections = []
    for group in groups:
        items = []
        for label, key in group["fields"]:
            values = []
            for i, dt in enumerate(dates):
                r = date_to_report.get(dt)
                if not r:
                    values.append(None)
                    continue
                raw = getattr(r, json_field) or {}
                val = _em_value(raw, key, is_eps=(key in eps_keys)) if key else None
                values.append(val)
            items.append({"name": label, "key": key or f"row_{len(items)}", "values": values})
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
    if isinstance(v, (int, float)):
        return float(v) if not is_eps else round(float(v), 4)
    s = str(v).strip().replace(",", "")
    if s in ("", "--", "-", "nan", "None"):
        return None
    try:
        fv = float(s)
        return fv if not is_eps else round(fv, 4)
    except (ValueError, TypeError):
        return None
