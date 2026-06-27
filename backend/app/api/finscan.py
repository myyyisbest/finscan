"""Finscan 排雷 API"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import Optional
from decimal import Decimal
import json

from app.db import get_db
from app.core.response import success_response, fail_response
from app.models import FinReport, StockBasic
from app.engine import RuleEngine, RuleContext, RiskLevel, Verdict

router = APIRouter(prefix="/api/v1/finscan", tags=["finscan"])


def _code_to_ts(code: str) -> str:
    """股票代码转东财格式"""
    code = code.strip()
    if code.startswith("6"):
        return f"SH{code}"
    elif code.startswith(("0", "3")):
        return f"SZ{code}"
    return f"SZ{code}"


def _ts_to_code(ts: str) -> str:
    """东财格式转股票代码"""
    return ts.replace("SH", "").replace("SZ", "").replace("BJ", "")


def _get_report_years(db: Session, stock_code: str, years: int = 5) -> list:
    """获取最近 N 年财报"""
    reports = (
        db.query(FinReport)
        .filter(FinReport.stock_code == stock_code)
        .filter(FinReport.report_type == "Annual")
        .order_by(desc(FinReport.report_date))
        .limit(years)
        .all()
    )
    return reports


def _build_rule_context(db: Session, stock_code: str, report_year: int) -> RuleContext:
    """从数据库构建规则上下文"""
    stock = db.query(StockBasic).filter(StockBasic.stock_code == stock_code).first()
    stock_name = stock.stock_name if stock else ""
    industry = stock.industry if stock else ""

    reports = _get_report_years(db, stock_code, 5)

    income_list = []
    balance_list = []
    cashflow_list = []
    indicator_list = []

    for i, r in enumerate(reports):
        income_json = r.income_json or {}
        balance_json = r.balance_json or {}
        cashflow_json = r.cashflow_json or {}

        revenue = income_json.get("TOTAL_OPERATE_INCOME") or income_json.get("OPERATE_INCOME")
        oper_cost = income_json.get("OPERATE_COST") or income_json.get("TOTAL_OPERATE_COST")
        gross_profit = None
        if revenue is not None and oper_cost is not None:
            try:
                gross_profit = float(revenue) - float(oper_cost)
            except (TypeError, ValueError):
                pass

        income_list.append({
            "end_date": str(r.report_date),
            "revenue": revenue,
            "revenue_yoy": income_json.get("TOTAL_OPERATE_INCOME_YOY") or income_json.get("OPERATE_INCOME_YOY"),
            "oper_cost": oper_cost,
            "gross_profit": gross_profit,
            "sell_exp": income_json.get("SALE_EXPENSE"),
            "admin_exp": income_json.get("MANAGE_EXPENSE"),
            "rd_exp": income_json.get("RESEARCH_EXPENSE"),
            "fin_exp": income_json.get("FINANCE_EXPENSE"),
            "assets_impair_loss": income_json.get("ASSET_IMPAIRMENT_LOSS"),
            "credit_impa_loss": income_json.get("CREDIT_IMPAIRMENT_INCOME"),
            "oth_biz_income": income_json.get("OTHER_INCOME"),
            "invest_income": income_json.get("INVEST_INCOME"),
            "operate_profit": income_json.get("OPERATE_PROFIT"),
            "net_profit": income_json.get("NETPROFIT"),
            "n_income_attr_p": income_json.get("PARENT_NETPROFIT"),
            "deduct_non_recurring": income_json.get("DEDUCT_PARENT_NETPROFIT"),
            "basic_eps": income_json.get("BASIC_EPS"),
        })

        balance_list.append({
            "end_date": str(r.report_date),
            "total_assets": balance_json.get("TOTAL_ASSETS"),
            "total_liab": balance_json.get("TOTAL_LIABILITIES") or balance_json.get("TOTAL_LIAB"),
            "total_hldr_eqy_exc_min_int": balance_json.get("TOTAL_EQUITY") or balance_json.get("TOTAL_PARENT_EQUITY"),
            "money_cap": balance_json.get("MONETARYFUNDS"),
            "accounts_receiv": balance_json.get("ACCOUNTS_RECE") or balance_json.get("NOTE_ACCOUNTS_RECE"),
            "oth_receiv": balance_json.get("TOTAL_OTHER_RECE") or balance_json.get("OTHER_RECEIVABLE"),
            "inventories": balance_json.get("INVENTORY"),
            "total_current_assets": balance_json.get("TOTAL_CURRENT_ASSETS"),
            "fix_assets": balance_json.get("FIXED_ASSET"),
            "cip": balance_json.get("CIP"),
            "goodwill": balance_json.get("GOODWILL"),
            "lt_amort_deferred_exp": balance_json.get("LONG_PREPAID_EXPENSE") or balance_json.get("LONG_TERM_PAYROLL_PAYABLE"),
            "intang_assets": balance_json.get("INTANGIBLE_ASSET"),
            "st_borr": balance_json.get("SHORT_LOAN") or balance_json.get("ST_BORR"),
            "lt_borr": balance_json.get("LONG_LOAN") or balance_json.get("LT_BORR"),
            "bond_payable": balance_json.get("BOND_PAYABLE"),
            "accounts_payable": balance_json.get("ACCOUNTS_PAYABLE") or balance_json.get("NOTE_ACCOUNTS_PAYABLE"),
            "advance_receipts": balance_json.get("ADVANCE_RECEIPTS"),
            "contract_liab": balance_json.get("CONTRACT_LIAB"),
            "total_current_liab": balance_json.get("TOTAL_CURRENT_LIAB"),
        })

        oper_cf = cashflow_json.get("NETCASH_OPERATE")
        invest_cf = cashflow_json.get("NETCASH_INVEST")
        construct_long = cashflow_json.get("CONSTRUCT_LONG_ASSET")
        free_cashflow = None
        try:
            if oper_cf is not None and construct_long is not None:
                free_cashflow = float(oper_cf) + float(construct_long)
            elif oper_cf is not None and invest_cf is not None:
                free_cashflow = float(oper_cf) + float(invest_cf)
        except (TypeError, ValueError):
            pass

        cashflow_list.append({
            "end_date": str(r.report_date),
            "n_cashflow_act": oper_cf,
            "n_cashflow_inv_act": invest_cf,
            "n_cash_flows_fnc_act": cashflow_json.get("NETCASH_FINANCE"),
            "c_recp_prov_sg_act": cashflow_json.get("SALES_SERVICES"),
            "c_pay_acq_const_fiolta": construct_long,
            "free_cashflow": free_cashflow,
        })

        inv_turn = None
        ar_turn = None
        try:
            inv_cur = float(balance_json.get("INVENTORY") or 0)
            inv_prev = float(reports[i + 1].balance_json.get("INVENTORY") or 0) if i + 1 < len(reports) else inv_cur
            avg_inv = (inv_cur + inv_prev) / 2 if inv_cur and inv_prev else inv_cur or inv_prev
            if avg_inv > 0 and oper_cost is not None:
                inv_turn = float(oper_cost) / avg_inv
        except (TypeError, ValueError, ZeroDivisionError):
            pass

        try:
            ar_cur = float(balance_json.get("ACCOUNTS_RECE") or balance_json.get("NOTE_ACCOUNTS_RECE") or 0)
            ar_prev = float(reports[i + 1].balance_json.get("ACCOUNTS_RECE") or reports[i + 1].balance_json.get("NOTE_ACCOUNTS_RECE") or 0) if i + 1 < len(reports) else ar_cur
            avg_ar = (ar_cur + ar_prev) / 2 if ar_cur and ar_prev else ar_cur or ar_prev
            if avg_ar > 0 and revenue is not None:
                ar_turn = float(revenue) / avg_ar
        except (TypeError, ValueError, ZeroDivisionError):
            pass

        indicator_list.append({
            "end_date": str(r.report_date),
            "roe": r.roe,
            "roa": r.roa,
            "grossprofit_margin": r.gross_margin,
            "netprofit_margin": r.net_margin,
            "revenue_yoy": r.revenue_yoy,
            "netprofit_yoy": r.net_profit_yoy,
            "debt_to_assets": r.debt_ratio,
            "current_ratio": r.current_ratio,
            "quick_ratio": r.quick_ratio,
            "inv_turn": inv_turn,
            "ar_turn": ar_turn,
            "assets_turn": None,
        })

    latest_report = reports[0] if reports else None
    audit_result = "标准无保留意见"
    ann_date = None
    end_date = None

    if latest_report:
        if latest_report.notice_date:
            ann_date = str(latest_report.notice_date)
        end_date = str(latest_report.report_date)

    return RuleContext(
        stock_code=stock_code,
        stock_name=stock_name,
        industry=industry,
        audit_result=audit_result,
        ann_date=ann_date,
        end_date=end_date,
        income_list=income_list,
        balance_list=balance_list,
        cashflow_list=cashflow_list,
        indicator_list=indicator_list,
    )


@router.get("/{code}/analyze")
def analyze_stock(
    code: str,
    year: Optional[int] = Query(None, description="分析年份，默认最新年报"),
    db: Session = Depends(get_db),
):
    """
    对指定股票进行财报排雷分析。

    返回完整的风险评估报告，包含：
    - 总风险评分与等级
    - 各规则判定结果（30条规则）
    - 组合加分
    """
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")

    # 检查股票是否存在
    stock = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
    if not stock:
        return fail_response(404, "股票不存在")

    # 获取分析年份
    if year is None:
        reports = _get_report_years(db, code, 1)
        year = reports[0].report_date.year if reports else 2025

    # 构建规则上下文
    ctx = _build_rule_context(db, code, year)

    # 执行分析
    engine = RuleEngine()
    result = engine.analyze(ctx, year)

    # 转换为响应格式
    response = result.to_dict()

    # 添加股票基本信息
    response["stock_info"] = {
        "code": code,
        "name": stock.stock_name,
        "industry": stock.industry,
        "list_date": str(stock.list_date) if stock.list_date else None,
    }

    return success_response(response)


@router.get("/{code}/history")
def get_analysis_history(
    code: str,
    db: Session = Depends(get_db),
):
    """获取股票历史分析记录"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")

    # 从已有数据计算历史分析
    reports = _get_report_years(db, code, 10)
    if not reports:
        return success_response([])

    history = []
    for r in reports:
        ctx = _build_rule_context(db, code, r.report_date.year)
        engine = RuleEngine()
        result = engine.analyze(ctx, r.report_date.year)

        history.append({
            "year": r.report_date.year,
            "report_date": str(r.report_date),
            "notice_date": str(r.notice_date) if r.notice_date else None,
            "total_score": result.total_score,
            "risk_level": result.risk_level.value,
            "n_pass": result.n_pass,
            "n_warn": result.n_warn,
            "n_fail": result.n_fail,
            "n_skip": result.n_skip,
            "combo_bonus": result.combo_bonus,
        })

    return success_response(history)


@router.get("/batch-scan")
def batch_scan(
    codes: str = Query(..., description="股票代码列表，逗号分隔"),
    db: Session = Depends(get_db),
):
    """
    批量扫描多只股票的排雷分析。

    适用于自选股批量筛查场景。
    """
    code_list = [c.strip().upper().replace("SH", "").replace("SZ", "").replace("BJ", "") for c in codes.split(",")]

    if len(code_list) > 50:
        return fail_response(400, "单次批量扫描最多支持50只股票")

    results = []
    engine = RuleEngine()

    for code in code_list:
        stock = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
        if not stock:
            results.append({
                "code": code,
                "error": "股票不存在",
            })
            continue

        reports = _get_report_years(db, code, 1)
        if not reports:
            results.append({
                "code": code,
                "name": stock.stock_name,
                "error": "无财报数据",
            })
            continue

        ctx = _build_rule_context(db, code, reports[0].report_date.year)
        result = engine.analyze(ctx, reports[0].report_date.year)

        results.append({
            "code": code,
            "name": stock.stock_name,
            "industry": stock.industry,
            "year": reports[0].report_date.year,
            "total_score": result.total_score,
            "risk_level": result.risk_level.value,
            "n_pass": result.n_pass,
            "n_warn": result.n_warn,
            "n_fail": result.n_fail,
            "combo_bonus": result.combo_bonus,
            # 高亮最严重的问题
            "top_warnings": [
                {
                    "code": r.code,
                    "name": r.name,
                    "verdict": r.verdict.value,
                    "detail": r.detail,
                }
                for r in result.rule_results
                if r.verdict in (Verdict.FAIL, Verdict.WARN)
            ][:3],
        })

    return success_response(results)


@router.get("/rules")
def list_rules():
    """
    获取所有排雷规则的说明。

    用于前端展示规则详情。
    """
    rules_info = [
        # Layer 0
        {"code": "0.1", "name": "审计意见", "layer": 0, "weight_fail": 999, "description": "必须为标准无保留意见，否则一票否决"},
        {"code": "0.2", "name": "按时披露", "layer": 0, "weight_fail": 999, "description": "年报必须在次年4月30日前披露"},
        # Layer 1
        {"code": "1.1", "name": "毛利率异常", "layer": 1, "weight_warn": 2, "weight_fail": 5, "description": "毛利率大幅波动或远超同行"},
        {"code": "1.2", "name": "营收虚增信号", "layer": 1, "weight_warn": 2, "weight_fail": 5, "description": "毛利率↑ + 应收↑ + 应付↓ 三信号叠加"},
        {"code": "1.3", "name": "运费增速异常", "layer": 1, "weight_warn": 2, "weight_fail": 5, "description": "运费增长远低于收入增长"},
        {"code": "1.4", "name": "其他业务收入异常", "layer": 1, "weight_warn": 2, "weight_fail": 5, "description": "其他业务收入占比突增"},
        {"code": "1.5", "name": "费用率异常下降", "layer": 1, "weight_warn": 2, "weight_fail": 5, "description": "三项费用率异常下降超过3pp"},
        {"code": "1.6", "name": "资产减值暴增", "layer": 1, "weight_warn": 2, "weight_fail": 5, "description": "资产减值损失同比暴增"},
        # Layer 2
        {"code": "2.1", "name": "投资支出异常", "layer": 2, "weight_warn": 3, "weight_fail": 6, "description": "经营CF良好但持续大额投资支出"},
        {"code": "2.2", "name": "经营现金流为负", "layer": 2, "weight_warn": 3, "weight_fail": 6, "description": "经营现金流持续为负"},
        {"code": "2.3", "name": "大存大贷", "layer": 2, "weight_warn": 3, "weight_fail": 6, "description": "货币资金和有息负债双高"},
        # Layer 3
        {"code": "3.1", "name": "应收增速异常", "layer": 3, "weight_warn": 2, "weight_fail": 5, "description": "应收账款增速远超营收增速"},
        {"code": "3.2", "name": "存货与毛利率背离", "layer": 3, "weight_warn": 2, "weight_fail": 5, "description": "存货周转率下降但毛利率上升"},
        {"code": "3.3", "name": "在建工程异常", "layer": 3, "weight_warn": 2, "weight_fail": 5, "description": "在建工程持续不转固"},
        {"code": "3.4", "name": "长期待摊费用异常", "layer": 3, "weight_warn": 2, "weight_fail": 5, "description": "长期待摊费用大增"},
        {"code": "3.5", "name": "坏账计提不足", "layer": 3, "weight_warn": 2, "weight_fail": 5, "description": "坏账计提比例显著低于同行"},
        # Layer 4
        {"code": "4.1", "name": "净现比异常", "layer": 4, "weight_warn": 3, "weight_fail": 7, "description": "经营现金流/净利润持续小于1"},
        {"code": "4.2", "name": "收现比异常", "layer": 4, "weight_warn": 3, "weight_fail": 7, "description": "销售收现/营收小于0.8"},
        {"code": "4.3", "name": "资产利润背离", "layer": 4, "weight_warn": 3, "weight_fail": 7, "description": "资产膨胀但利润未相应增长"},
        {"code": "4.4", "name": "核心利润背离", "layer": 4, "weight_warn": 3, "weight_fail": 7, "description": "核心利润与净利润背离超过40%"},
        {"code": "4.5", "name": "盈利与自由现金背离", "layer": 4, "weight_warn": 3, "weight_fail": 7, "description": "净利润增长但FCF持续为负"},
        # Layer 5
        {"code": "5.1", "name": "更换审计机构", "layer": 5, "weight_warn": 1, "weight_fail": 3, "description": "频繁更换审计机构"},
        {"code": "5.2", "name": "大股东减持", "layer": 5, "weight_warn": 1, "weight_fail": 3, "description": "大股东持续减持"},
        {"code": "5.3", "name": "高管变更", "layer": 5, "weight_warn": 1, "weight_fail": 3, "description": "财务总监频繁更换"},
        {"code": "5.4", "name": "独董辞职", "layer": 5, "weight_warn": 1, "weight_fail": 3, "description": "独立董事集体辞职"},
        {"code": "5.5", "name": "客户集中度", "layer": 5, "weight_warn": 1, "weight_fail": 3, "description": "客户集中度过高"},
        {"code": "5.6", "name": "频繁并购", "layer": 5, "weight_warn": 1, "weight_fail": 3, "description": "跨行业频繁收购"},
        # Layer 6
        {"code": "6.1", "name": "行业风险", "layer": 6, "weight_warn": 1, "weight_fail": 3, "description": "农林渔牧等难以审计的行业"},
        {"code": "6.2", "name": "研发资本化", "layer": 6, "weight_warn": 1, "weight_fail": 3, "description": "研发资本化比例超过50%"},
    ]

    return success_response(rules_info)
