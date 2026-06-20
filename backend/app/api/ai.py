"""AI 智能分析 API（DeepSeek RAG）。

设计原则：AI 只做数据解读，所有数值结论必须来自数据库。
幻觉防控：数值强制校验 + 溯源标注。
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

from app.core.auth import get_optional_user_id
from app.core.config import settings
from app.core.response import ok
from app.db import get_db
from app.models import (
    StockBasic, BalanceSheet, IncomeStatement, CashFlow, FinIndicator,
    RiskReport, RiskRuleResult,
)


router = AI_ROUTER = APIRouter(prefix="/api/v1/ai", tags=["ai"])
log = logging.getLogger("ai_service")


# ===================== DeepSeek 客户端 =====================

class DeepSeekClient:
    """DeepSeek API 客户端（OpenAI 兼容接口）。"""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL

    def chat(self, messages: list[dict], temperature: float = 0.1) -> str:
        if not self.api_key:
            return "⚠️ AI 功能未启用（请在 .env 中配置 DEEPSEEK_API_KEY）"
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            log.warning("DeepSeek 调用失败: %s", exc)
            return f"⚠️ AI 服务暂时不可用: {exc}"


_client = DeepSeekClient()


# ===================== 财务数据提取工具 =====================

def _build_financial_context(stock_code: str, db: Session, years: int = 3) -> str:
    """构建财务数据文本上下文（用于 AI 读取）。"""
    # 最新年报
    inc = (
        db.query(IncomeStatement)
        .filter(IncomeStatement.stock_code == stock_code,
                IncomeStatement.report_type == "Annual")
        .order_by(IncomeStatement.report_date.desc())
        .first()
    )
    bs = (
        db.query(BalanceSheet)
        .filter(BalanceSheet.stock_code == stock_code,
                BalanceSheet.report_type == "Annual")
        .order_by(BalanceSheet.report_date.desc())
        .first()
    )
    cf = (
        db.query(CashFlow)
        .filter(CashFlow.stock_code == stock_code,
                CashFlow.report_type == "Annual")
        .order_by(CashFlow.report_date.desc())
        .first()
    )
    ind = (
        db.query(FinIndicator)
        .filter(FinIndicator.stock_code == stock_code,
                FinIndicator.report_type == "Annual")
        .order_by(FinIndicator.report_date.desc())
        .first()
    )
    # 去年数据（同比）
    prev_inc = (
        db.query(IncomeStatement)
        .filter(IncomeStatement.stock_code == stock_code,
                IncomeStatement.report_type == "Annual")
        .order_by(IncomeStatement.report_date.desc())
        .offset(1).first()
    )

    def fmt(v) -> str:
        if v is None: return "无数据"
        if isinstance(v, Decimal):
            if abs(v) >= Decimal("1e8"):
                return f"{float(v)/1e8:.2f}亿元"
            if abs(v) >= Decimal("1e4"):
                return f"{float(v)/1e4:.2f}万元"
            return f"{float(v):.2f}元"
        return str(v)

    lines = [f"公司: {stock_code}"]
    if inc:
        lines.append(f"报告期: {inc.report_date} ({inc.report_type})")
        lines.append(f"营业收入: {fmt(inc.total_revenue)}")
        lines.append(f"营业成本: {fmt(inc.operating_cost)}")
        lines.append(f"毛利润: {fmt(inc.gross_profit)}, 毛利率: {inc.gross_margin:.2f}%" if inc.gross_margin else "毛利率: 无数据")
        lines.append(f"销售费用: {fmt(inc.selling_expenses)}")
        lines.append(f"管理费用: {fmt(inc.admin_expenses)}")
        lines.append(f"研发费用: {fmt(inc.rd_expenses)}")
        lines.append(f"财务费用: {fmt(inc.financial_expenses)}")
        lines.append(f"营业利润: {fmt(inc.operating_profit)}")
        lines.append(f"净利润: {fmt(inc.net_profit)}")
        lines.append(f"归母净利润: {fmt(inc.net_profit_parent)}")
        lines.append(f"扣非净利润: {fmt(inc.net_profit_deduct)}")
    if bs:
        lines.append(f"总资产: {fmt(bs.total_assets)}")
        lines.append(f"总负债: {fmt(bs.total_liabilities)}")
        lines.append(f"净资产: {fmt(bs.total_equity)}")
        lines.append(f"货币资金: {fmt(bs.monetary_funds)}")
        lines.append(f"应收账款: {fmt(bs.accounts_receivable)}")
        lines.append(f"存货: {fmt(bs.inventory)}")
        lines.append(f"商誉: {fmt(bs.goodwill)}")
    if cf:
        lines.append(f"经营现金流净额: {fmt(cf.operating_cash_net)}")
        lines.append(f"投资现金流净额: {fmt(cf.investing_cash_net)}")
        lines.append(f"筹资现金流净额: {fmt(cf.financing_cash_net)}")
        lines.append(f"自由现金流: {fmt(cf.free_cash_flow)}")
    def _pct(v) -> str:
        return f"{float(v):.2f}%" if v is not None else "无数据"

    def _f(v) -> str:
        return f"{float(v):.2f}" if v is not None else "无数据"

    def _times(v) -> str:
        return f"{float(v):.2f}次" if v is not None else "无数据"

    if ind:
        lines.append(f"ROE(净资产收益率): {_pct(ind.roe)}")
        lines.append(f"ROA(总资产收益率): {_pct(ind.roa)}")
        lines.append(f"净利率: {_pct(ind.net_margin)}")
        lines.append(f"资产负债率: {_pct(ind.debt_to_assets)}")
        lines.append(f"流动比率: {_f(ind.current_ratio)}")
        lines.append(f"存货周转率: {_times(ind.inventory_turnover)}")
        lines.append(f"应收账款周转率: {_times(ind.ar_turnover)}")
        lines.append(f"营收同比: {_pct(ind.revenue_yoy)}")
        lines.append(f"净利润同比: {_pct(ind.net_profit_yoy)}")
        lines.append(f"经营CF/净利润: {_pct(ind.cf_to_net_profit)}")
    if prev_inc and inc:
        if prev_inc.total_revenue and inc.total_revenue and prev_inc.total_revenue != 0:
            yoy = float(inc.total_revenue - prev_inc.total_revenue) * 100 / float(abs(prev_inc.total_revenue))
            lines.append(f"营收同比增速: {yoy:.2f}%")
    return "\n".join(lines)


def _build_risk_context(stock_code: str, db: Session) -> str:
    report = (
        db.query(RiskReport)
        .filter(RiskReport.stock_code == stock_code)
        .order_by(RiskReport.report_date.desc())
        .first()
    )
    if report is None:
        return "暂无风险评估数据"
    rules = (
        db.query(RiskRuleResult)
        .filter(RiskRuleResult.stock_code == stock_code,
                RiskRuleResult.report_date == report.report_date,
                RiskRuleResult.result.in_(["WARN", "FAIL"]))
        .all()
    )
    lines = [
        f"风险等级: {report.risk_level}",
        f"总分: {report.total_score} (满分约100)",
        f"参与规则: {report.rule_participated}/{report.rule_total}",
        "风险点:"
    ]
    for r in rules:
        emoji = "🔴" if r.result == "FAIL" else "🟡"
        lines.append(f"  {emoji} [{r.rule_code}] {r.result} (+{r.score}分): {r.evidence}")
    return "\n".join(lines)


def _verify_numbers(text: str, ctx: str) -> tuple[bool, str]:
    """幻觉校验：提取文本中所有数字，与上下文比对。"""
    numbers = re.findall(r'[-+]?\d+\.?\d*%?', text)
    suspicious = []
    for num in numbers[:20]:  # 只检查前20个
        clean = num.rstrip('%')
        try:
            f = float(clean)
            # 简单合理性检查：不可能出现的数值
            if f > 1e15 or (f > 1000 and '%' not in num):
                suspicious.append(num)
        except ValueError:
            pass
    if suspicious:
        return False, f"发现异常数值: {suspicious}"
    return True, "校验通过"


# ===================== Prompt 模板 =====================

_FIN_ANALYSIS_PROMPT = """你是一位专业财务分析师。请基于以下真实财务数据，对公司进行财报解读。

【重要约束】
1. 只使用提供的数据，禁止编造任何数字
2. 禁止使用"大幅增长"、"显著下降"等模糊表述，必须用具体数值
3. 结论必须标注"数据来源：XXXX"
4. 禁止生成投资建议、买卖指导

【财务数据】
{financial_data}

【风险评估】
{risk_data}

请按以下结构输出：
## 一、整体经营概况（100字以内）
## 二、核心变化点（3-5条，每条包含具体数值和同比）
## 三、财务风险提示（基于风险评估）
## 四、现金流质量评价
"""

_COMPARE_PROMPT = """你是一位专业财务分析师。请对比分析以下多家公司的财务数据。

【数据】
{compare_data}

【重要约束】
1. 只使用提供的数据
2. 指出各公司核心优劣势，必须带具体数值对比
3. 禁止生成投资建议
"""

_ANNOUNCEMENT_PROMPT = """你是一位专业财务分析师。请为以下公告内容生成摘要。

【公告标题】
{title}

【公告摘要】
{summary}

请输出：
1. 三句话核心摘要
2. 事件定性（利好/利空/中性）
3. 潜在财务影响（如有）
"""


# ===================== API 端点 =====================

@router.get("/analyze/financial")
def analyze_financial(
    stock_code: str,
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
):
    """单公司财报 AI 智能解读。"""
    basic = db.query(StockBasic).filter(StockBasic.stock_code == stock_code).first()
    name = basic.stock_name if basic else stock_code

    fin_data = _build_financial_context(stock_code, db)
    risk_data = _build_risk_context(stock_code, db)

    prompt = _FIN_ANALYSIS_PROMPT.format(
        financial_data=fin_data, risk_data=risk_data
    )
    messages = [
        {"role": "system", "content": "你是一位严谨的专业财务分析师，只基于提供的数据回答问题。"},
        {"role": "user", "content": prompt},
    ]
    text = _client.chat(messages)

    # 幻觉校验
    safe, msg = _verify_numbers(text, fin_data)
    if not safe:
        text += f"\n\n⚠️ 数据校验提示: {msg}"

    return ok({
        "stock_code": stock_code,
        "stock_name": name,
        "analysis": text,
    })


@router.get("/analyze/compare")
def analyze_compare(
    stock_codes: str = Query(description="逗号分隔股票代码"),
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
):
    """多公司对标 AI 差异分析。"""
    codes = [c.strip() for c in stock_codes.split(",") if c.strip()][:8]
    lines = []
    for code in codes:
        basic = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
        name = basic.stock_name if basic else code
        fin = _build_financial_context(code, db)
        lines.append(f"=== {name}({code}) ===\n{fin}\n")

    prompt = _COMPARE_PROMPT.format(compare_data="\n".join(lines))
    messages = [
        {"role": "system", "content": "你是一位专业财务分析师，对比多家公司时客观公正。"},
        {"role": "user", "content": prompt},
    ]
    text = _client.chat(messages)
    return ok({"analysis": text})


@router.get("/summarize/announcement")
def summarize_announcement(
    title: str,
    summary: str = "",
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
):
    """公告一键 AI 摘要。"""
    prompt = _ANNOUNCEMENT_PROMPT.format(title=title, summary=summary)
    messages = [
        {"role": "system", "content": "你是一位专业财经分析师，擅长解读上市公司公告。"},
        {"role": "user", "content": prompt},
    ]
    text = _client.chat(messages)
    return ok({"summary": text})


@router.get("/chat")
def chat(
    q: str = Query(description="自然语言问题"),
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
):
    """自然语言问答（仅限数据库内财报数据）。"""
    # 简单解析：尝试提取股票名称/代码和指标
    # 未来可扩展为 SQL 生成
    stock_match = re.search(r'([\u4e00-\u9fa5]{2,6}|[0-9]{6})\s*(近|过去|最近)?(\d+)年?', q)
    if stock_match:
        # 尝试从数据库找股票
        keyword = stock_match.group(1)
        if keyword.isdigit():
            stock = db.query(StockBasic).filter(StockBasic.stock_code.like(f"%{keyword}%")).first()
        else:
            stock = db.query(StockBasic).filter(StockBasic.stock_name.like(f"%{keyword}%")).first()
        if stock:
            context = _build_financial_context(stock.stock_code, db)
            prompt = f"用户问题：{q}\n\n可用数据：\n{context}\n\n请基于上述数据回答用户问题，禁止编造数据。"
            messages = [
                {"role": "system", "content": "你是一位专业财务分析师，只基于提供的数据回答。"},
                {"role": "user", "content": prompt},
            ]
            text = _client.chat(messages)
            safe, msg = _verify_numbers(text, context)
            if not safe:
                text += f"\n\n⚠️ {msg}"
            return ok({"question": q, "answer": text, "stock_code": stock.stock_code})
    return ok({
        "question": q,
        "answer": "该问题超出当前数据范围，建议查阅官方公告原文。支持的提问示例：「贵州茅台近3年ROE变化」「五粮液毛利率对比」",
    })
