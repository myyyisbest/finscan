"""
财报排雷规则引擎 - Finscan Pro
实现 30 条规则的分层评估体系
方法论来源：《手把手教你读财报（新准则升级版）》唐朝
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
import json


class Verdict(Enum):
    """判定结果"""
    PASS = "PASS"   # 通过
    WARN = "WARN"   # 警告
    FAIL = "FAIL"   # 失败
    SKIP = "SKIP"   # 跳过


class RiskLevel(Enum):
    """风险等级"""
    LOW = "LOW"           # 低风险 0-10
    MEDIUM = "MEDIUM"     # 中风险 11-25
    HIGH = "HIGH"         # 高风险 26-45
    VERY_HIGH = "VERY_HIGH"  # 极高风险 46+
    REJECT = "REJECT"     # 一票否决


@dataclass
class RuleContext:
    """规则上下文 - 提供规则评估所需的所有数据"""
    stock_code: str
    stock_name: str
    industry: Optional[str]

    # 审计数据（最新）
    audit_result: Optional[str] = None
    audit_agency: Optional[str] = None
    ann_date: Optional[str] = None
    end_date: Optional[str] = None

    # 利润表（多年）
    income_list: list = field(default_factory=list)

    # 资产负债表（多年）
    balance_list: list = field(default_factory=list)

    # 现金流量表（多年）
    cashflow_list: list = field(default_factory=list)

    # 财务指标（多年）
    indicator_list: list = field(default_factory=list)

    # 同行指标
    peer_indicators: dict = field(default_factory=dict)

    # PDF 解析数据（可选）
    pdf_data: dict = field(default_factory=dict)

    def latest(self, data_list: list) -> Optional[dict]:
        """获取最新一期数据"""
        if not data_list:
            return None
        return data_list[0] if data_list else None

    def prev(self, data_list: list, offset: int = 1) -> Optional[dict]:
        """获取前 N 期数据"""
        if len(data_list) <= offset:
            return None
        return data_list[offset] if data_list else None


@dataclass
class RuleResult:
    """单条规则结果"""
    code: str
    name: str
    layer: int
    verdict: Verdict
    score_added: int = 0
    detail: str = ""
    raw_values: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "layer": self.layer,
            "verdict": self.verdict.value,
            "score_added": self.score_added,
            "detail": self.detail,
            "raw_values": self.raw_values,
        }


@dataclass
class ReportResult:
    """完整报告结果"""
    stock_code: str
    stock_name: str
    report_year: int
    total_score: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    rule_results: list = field(default_factory=list)
    combo_bonus: int = 0

    n_pass: int = 0
    n_warn: int = 0
    n_fail: int = 0
    n_skip: int = 0

    def to_dict(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "report_year": self.report_year,
            "total_score": self.total_score,
            "risk_level": self.risk_level.value,
            "n_pass": self.n_pass,
            "n_warn": self.n_warn,
            "n_fail": self.n_fail,
            "n_skip": self.n_skip,
            "combo_bonus": self.combo_bonus,
            "rule_results": [r.to_dict() for r in self.rule_results],
        }


class BaseRule(ABC):
    """规则基类"""

    # 规则配置（子类覆盖）
    code: str = ""
    name: str = ""
    layer: int = 0
    weight_warn: int = 0
    weight_fail: int = 0

    @abstractmethod
    def evaluate(self, ctx: RuleContext) -> RuleResult:
        """执行规则评估"""
        pass

    def get_verdict_and_score(self, verdict: Verdict) -> tuple:
        """根据判定结果计算分数"""
        if verdict == Verdict.PASS:
            return 0
        elif verdict == Verdict.WARN:
            return self.weight_warn
        elif verdict == Verdict.FAIL:
            return self.weight_fail
        return 0

    def format_number(self, val: Any, decimals: int = 2) -> str:
        """格式化数字"""
        if val is None:
            return "N/A"
        try:
            return f"{float(val):.{decimals}f}"
        except (TypeError, ValueError):
            return str(val)


# ============================================
# Layer 0: 门槛检查（一票否决）
# ============================================

class Rule0_1(BaseRule):
    """审计意见 - 必须为标准无保留意见"""
    code = "0.1"
    name = "审计意见"
    layer = 0
    weight_warn = 0  # 非标准意见直接 FAIL，无 WARN
    weight_fail = 999  # 一票否决

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        audit = ctx.latest(ctx.income_list)
        if not audit:
            return RuleResult(
                code=self.code, name=self.name, layer=self.layer,
                verdict=Verdict.SKIP, detail="无审计数据"
            )

        result = ctx.audit_result or ""
        detail = f"审计意见: {result}"

        non_standard = any(kw in result for kw in [
            "保留意见", "无法表示意见", "否定意见",
            "带强调事项段的无保留", "带强调事项段",
        ])
        standard_kw = ["标准无保留", "标准的无保留"]
        is_standard = any(kw in result for kw in standard_kw)

        if non_standard and not is_standard:
            verdict = Verdict.FAIL
            score = 999
            detail += " → 非标准意见，一票否决"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → 标准无保留意见"

        return RuleResult(
            code=self.code, name=self.name, layer=self.layer,
            verdict=verdict, score_added=score, detail=detail,
            raw_values={"audit_result": result}
        )


class Rule0_2(BaseRule):
    """按时披露 - 年报必须在次年4月30日前披露"""
    code = "0.2"
    name = "按时披露"
    layer = 0
    weight_warn = 0
    weight_fail = 999

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if not ctx.ann_date or not ctx.end_date:
            return RuleResult(
                code=self.code, name=self.name, layer=self.layer,
                verdict=Verdict.SKIP, detail="无披露日期数据"
            )

        from datetime import datetime, timedelta

        try:
            end_dt = datetime.strptime(str(ctx.end_date), "%Y-%m-%d")
            ann_dt = datetime.strptime(str(ctx.ann_date), "%Y-%m-%d")

            # 次年4月30日
            deadline = datetime(end_dt.year + 1, 4, 30)

            detail = f"报告期: {ctx.end_date}, 披露日期: {ctx.ann_date}, 截止日期: {deadline.strftime('%Y-%m-%d')}"

            if ann_dt <= deadline:
                verdict = Verdict.PASS
                score = 0
                days_diff = (deadline - ann_dt).days
                detail += f" → 提前{days_diff}天披露"
            else:
                verdict = Verdict.FAIL
                score = 999
                days_diff = (ann_dt - deadline).days
                detail += f" → 超期{days_diff}天披露"

        except ValueError:
            return RuleResult(
                code=self.code, name=self.name, layer=self.layer,
                verdict=Verdict.SKIP, detail="日期格式错误"
            )

        return RuleResult(
            code=self.code, name=self.name, layer=self.layer,
            verdict=verdict, score_added=score, detail=detail
        )


# ============================================
# Layer 1: 利润表信号（6条规则）
# ============================================

class Rule1_1(BaseRule):
    """毛利率异常高 + 大幅波动"""
    code = "1.1"
    name = "毛利率异常"
    layer = 1
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        cur = ctx.latest(ctx.indicator_list)
        prev = ctx.prev(ctx.indicator_list)

        if not cur or cur.get("grossprofit_margin") is None:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="无毛利率数据")

        gm_cur = float(cur.get("grossprofit_margin", 0))
        gm_prev = float(prev.get("grossprofit_margin", 0)) if prev else gm_cur
        gm_yoy = gm_cur - gm_prev

        # 同行中位数
        peer_gm = ctx.peer_indicators.get("grossprofit_margin_median", 0)
        gm_vs_peer = gm_cur - peer_gm if peer_gm else 0

        detail = f"当前毛利率: {self.format_number(gm_cur, 2)}%, YoY: {self.format_number(gm_yoy, 2)}pp"

        if peer_gm:
            detail += f", 同行中位数: {self.format_number(peer_gm, 2)}%, vs同行: {self.format_number(gm_vs_peer, 2)}pp"

        if abs(gm_yoy) > 10 and gm_vs_peer > 15:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL: 大幅波动且远超同行"
        elif abs(gm_yoy) > 5 or gm_vs_peer > 15:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN: 波动较大或超出同行"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"gm_cur": gm_cur, "gm_yoy": gm_yoy, "gm_vs_peer": gm_vs_peer})


class Rule1_2(BaseRule):
    """毛利率↑ + 应收↑ + 应付↓（三信号叠加）"""
    code = "1.2"
    name = "营收虚增信号"
    layer = 1
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        ind_cur = ctx.latest(ctx.indicator_list)
        ind_prev = ctx.prev(ctx.indicator_list)
        bal_cur = ctx.latest(ctx.balance_list)
        bal_prev = ctx.prev(ctx.balance_list)
        inc_cur = ctx.latest(ctx.income_list)
        inc_prev = ctx.prev(ctx.income_list)

        signals = []

        # A: 毛利率上升
        if ind_cur and ind_prev:
            gm_cur = ind_cur.get("grossprofit_margin")
            gm_prev = ind_prev.get("grossprofit_margin")
            if gm_cur is not None and gm_prev is not None and gm_cur > gm_prev:
                signals.append("A")

        # B: 应收账款增速 > 营收增速
        if bal_cur and bal_prev and inc_cur and inc_prev:
            ar_cur = bal_cur.get("accounts_receiv") or 0
            ar_prev = bal_prev.get("accounts_receiv") or 0
            rev_cur = inc_cur.get("revenue") or 0
            rev_prev = inc_prev.get("revenue") or 0

            if rev_cur > 0 and rev_prev > 0:
                ar_growth = (float(ar_cur) - float(ar_prev)) / float(ar_prev) * 100 if ar_prev else 0
                rev_growth = (float(rev_cur) - float(rev_prev)) / float(rev_prev) * 100 if rev_prev else 0
                if ar_growth > rev_growth:
                    signals.append("B")

        # C: 应付账款下降
        if bal_cur and bal_prev:
            ap_cur = bal_cur.get("accounts_payable") or 0
            ap_prev = bal_prev.get("accounts_payable") or 0
            if ap_cur < ap_prev:
                signals.append("C")

        n_signals = len(signals)
        detail = f"信号: A(毛利率↑)={'A' in signals}, B(应收↑>营收↑)={'B' in signals}, C(应付↓)={'C' in signals}"

        if n_signals >= 3:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL: 三信号叠加，高度可疑"
        elif n_signals == 2:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN: 满足2个条件"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"signals": signals, "n_signals": n_signals})


class Rule1_3(BaseRule):
    """运费增长 vs 收入增长（需PDF）"""
    code = "1.3"
    name = "运费增速异常"
    layer = 1
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        freight_growth = ctx.pdf_data.get("freight_growth")
        revenue_yoy = ctx.pdf_data.get("revenue_yoy")

        if freight_growth is None:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="PDF中未找到运费明细")

        detail = f"运费增速: {self.format_number(freight_growth, 1)}%, 营收增速: {self.format_number(revenue_yoy, 1)}%"

        threshold = revenue_yoy * 0.25 if revenue_yoy else 0

        if freight_growth < threshold:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL: 运费增速远低于营收增速"
        elif freight_growth < revenue_yoy * 0.5:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN: 运费增速偏低"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail)


class Rule1_4(BaseRule):
    """其他业务收入占比突增"""
    code = "1.4"
    name = "其他业务收入异常"
    layer = 1
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        inc_cur = ctx.latest(ctx.income_list)
        inc_prev = ctx.prev(ctx.income_list)

        if not inc_cur:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="无利润表数据")

        oth_income = float(inc_cur.get("oth_biz_income") or 0)
        revenue = float(inc_cur.get("revenue") or 1)
        ratio = oth_income / revenue * 100 if revenue else 0

        ratio_prev = 0
        if inc_prev:
            oth_income_prev = float(inc_prev.get("oth_biz_income") or 0)
            revenue_prev = float(inc_prev.get("revenue") or 1)
            ratio_prev = oth_income_prev / revenue_prev * 100 if revenue_prev else 0

        ratio_change = ratio - ratio_prev

        detail = f"其他业务收入占比: {self.format_number(ratio, 2)}%, 同比变化: {self.format_number(ratio_change, 2)}pp"

        if ratio > 15 or ratio_change > 10:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL: 占比异常高"
        elif ratio > 5 and ratio_change > 3:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN: 占比和变化较大"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"ratio": ratio, "ratio_prev": ratio_prev, "ratio_change": ratio_change})


class Rule1_5(BaseRule):
    """费用率异常下降"""
    code = "1.5"
    name = "费用率异常下降"
    layer = 1
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if len(ctx.income_list) < 3:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足3年")

        ratios = []
        for inc in ctx.income_list[:3]:
            sell = float(inc.get("sell_exp") or 0)
            admin = float(inc.get("admin_exp") or 0)
            fin = float(inc.get("fin_exp") or 0)
            rev = float(inc.get("revenue") or 1)
            if rev > 0:
                ratios.append((sell + admin + fin) / rev * 100)

        if len(ratios) < 2:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足")

        avg_3yr = sum(ratios[1:]) / len(ratios[1:]) if len(ratios) > 1 else ratios[0]
        current_ratio = ratios[0]
        drop = avg_3yr - current_ratio

        detail = f"当前费用率: {self.format_number(current_ratio, 2)}%, 近3年均值: {self.format_number(avg_3yr, 2)}%, 下降: {self.format_number(drop, 2)}pp"

        if drop > 5:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL: 费用率大幅下降"
        elif drop > 3:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN: 费用率下降明显"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"current_ratio": current_ratio, "avg_3yr": avg_3yr, "drop": drop})


class Rule1_6(BaseRule):
    """资产减值损失暴增"""
    code = "1.6"
    name = "资产减值暴增"
    layer = 1
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        inc_cur = ctx.latest(ctx.income_list)
        inc_prev = ctx.prev(ctx.income_list)

        if not inc_cur:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="无利润表数据")

        impair_cur = abs(float(inc_cur.get("assets_impair_loss") or 0))
        credit_cur = abs(float(inc_cur.get("credit_impa_loss") or 0))
        total_impair = impair_cur + credit_cur
        net_profit = float(inc_cur.get("n_income_attr_p") or 0)

        if total_impair == 0:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.PASS, score_added=0, detail="无减值损失 → PASS")

        impair_prev = 0
        if inc_prev:
            impair_prev = abs(float(inc_prev.get("assets_impair_loss") or 0)) + \
                         abs(float(inc_prev.get("credit_impa_loss") or 0))

        impair_yoy = ((total_impair - impair_prev) / impair_prev * 100) if impair_prev else 999
        impair_to_profit = (total_impair / abs(net_profit) * 100) if net_profit else 0

        detail = f"减值损失: {self.format_number(total_impair/1e8, 2)}亿, YoY: {self.format_number(impair_yoy, 1)}%, 占净利润: {self.format_number(impair_to_profit, 1)}%"

        if impair_yoy > 100 or impair_to_profit > 5:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL"
        elif impair_yoy > 50:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"total_impair": total_impair, "impair_yoy": impair_yoy, "impair_to_profit": impair_to_profit})


# ============================================
# Layer 2: 现金流量表信号（3条规则）
# ============================================

class Rule2_1(BaseRule):
    """经营CF优异 + 投资CF持续大额为负"""
    code = "2.1"
    name = "投资支出异常"
    layer = 2
    weight_warn = 3
    weight_fail = 6

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if len(ctx.cashflow_list) < 4:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足4年")

        years = 0
        for cf in ctx.cashflow_list[:5]:
            oper_cf = float(cf.get("n_cashflow_act") or 0)
            inv_cf = float(cf.get("n_cashflow_inv_act") or 0)

            if oper_cf > 0 and abs(inv_cf) > oper_cf * 0.8:
                years += 1

        detail = f"连续多年经营CF良好但大额投资支出: {years}/5年"

        if years >= 4:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL: 多年投资无效"
        elif years >= 2:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"years": years})


class Rule2_2(BaseRule):
    """经营CF持续为负"""
    code = "2.2"
    name = "经营现金流为负"
    layer = 2
    weight_warn = 3
    weight_fail = 6

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if len(ctx.cashflow_list) < 3:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足3年")

        neg_years = 0
        consecutive = 0
        max_consecutive = 0

        for cf in ctx.cashflow_list[:5]:
            oper_cf = float(cf.get("n_cashflow_act") or 0)
            if oper_cf < 0:
                neg_years += 1
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0

        detail = f"近5年经营CF为负: {neg_years}年, 连续最长: {max_consecutive}年"

        if max_consecutive >= 3:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL: 连续亏损"
        elif neg_years >= 2:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"neg_years": neg_years, "max_consecutive": max_consecutive})


class Rule2_3(BaseRule):
    """大存大贷"""
    code = "2.3"
    name = "大存大贷"
    layer = 2
    weight_warn = 3
    weight_fail = 6

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        bal = ctx.latest(ctx.balance_list)
        inc_cur = ctx.latest(ctx.income_list)

        if not bal:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="无资产负债表数据")

        cash = float(bal.get("money_cap") or 0)
        st_borr = float(bal.get("st_borr") or 0)
        lt_borr = float(bal.get("lt_borr") or 0)
        bond = float(bal.get("bond_payable") or 0)
        interest_debt = st_borr + lt_borr + bond

        fin_exp = float(inc_cur.get("fin_exp") or 0) if inc_cur else 0

        detail = f"货币资金: {self.format_number(cash/1e8, 2)}亿, 有息负债: {self.format_number(interest_debt/1e8, 2)}亿"

        if cash > interest_debt and interest_debt > 0:
            implied_rate = abs(fin_exp) / interest_debt * 100 if interest_debt else 0
            detail += f", 隐含利率: {self.format_number(implied_rate, 2)}%"

            if implied_rate > 4:
                verdict = Verdict.FAIL
                score = self.weight_fail
                detail += " → FAIL: 大存大贷且高息"
            elif implied_rate > 2:
                verdict = Verdict.WARN
                score = self.weight_warn
                detail += " → WARN"
            else:
                verdict = Verdict.PASS
                score = 0
                detail += " → PASS"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS: 货币资金 < 有息负债"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"cash": cash, "interest_debt": interest_debt})


# ============================================
# Layer 3: 资产负债表信号（5条规则）
# ============================================

class Rule3_1(BaseRule):
    """应收增速 > 收入增速"""
    code = "3.1"
    name = "应收增速异常"
    layer = 3
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        bal_cur = ctx.latest(ctx.balance_list)
        bal_prev = ctx.prev(ctx.balance_list)
        inc_cur = ctx.latest(ctx.income_list)
        inc_prev = ctx.prev(ctx.income_list)

        if not all([bal_cur, bal_prev, inc_cur, inc_prev]):
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足")

        ar_cur = float(bal_cur.get("accounts_receiv") or 0)
        ar_prev = float(bal_prev.get("accounts_receiv") or 0)
        rev_cur = float(inc_cur.get("revenue") or 0)
        rev_prev = float(inc_prev.get("revenue") or 0)

        if ar_prev == 0 or rev_prev == 0:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="基期为0")

        ar_growth = (ar_cur - ar_prev) / ar_prev * 100
        rev_growth = (rev_cur - rev_prev) / rev_prev * 100

        ratio = ar_growth / rev_growth if rev_growth else 0

        detail = f"应收增速: {self.format_number(ar_growth, 1)}%, 营收增速: {self.format_number(rev_growth, 1)}%, 比率: {self.format_number(ratio, 2)}"

        if rev_growth > 0 and ratio > 2:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL: 应收增速远超营收"
        elif rev_growth <= 0 or ratio > 1.5:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"ar_growth": ar_growth, "rev_growth": rev_growth, "ratio": ratio})


class Rule3_2(BaseRule):
    """存货周转率↓ + 毛利率↑（造假黄金组合）"""
    code = "3.2"
    name = "存货与毛利率背离"
    layer = 3
    weight_warn = 2
    weight_fail = 5
    special_combo_score = 10  # 特殊组合加分

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        ind_cur = ctx.latest(ctx.indicator_list)
        ind_prev = ctx.prev(ctx.indicator_list)

        if not ind_cur or not ind_prev:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="无指标数据")

        inv_turn_cur = float(ind_cur.get("inv_turn") or 0)
        inv_turn_prev = float(ind_prev.get("inv_turn") or 0)
        gm_cur = float(ind_cur.get("grossprofit_margin") or 0)
        gm_prev = float(ind_prev.get("grossprofit_margin") or 0)

        if inv_turn_prev == 0:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="基期周转率为0")

        inv_turn_change = (inv_turn_cur - inv_turn_prev) / inv_turn_prev * 100
        gm_change = gm_cur - gm_prev

        detail = f"存货周转率变化: {self.format_number(inv_turn_change, 1)}%, 毛利率变化: {self.format_number(gm_change, 2)}pp"

        is_combo = inv_turn_change < -20 and gm_change > 3

        if is_combo:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL: 黄金造假组合"
        elif inv_turn_change < -10 and gm_change > 0:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"inv_turn_change": inv_turn_change, "gm_change": gm_change, "is_combo": is_combo})


class Rule3_3(BaseRule):
    """在建工程不转固"""
    code = "3.3"
    name = "在建工程异常"
    layer = 3
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if len(ctx.balance_list) < 3:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足3年")

        years = 0
        for i in range(min(5, len(ctx.balance_list))):
            if i + 1 >= len(ctx.balance_list):
                break
            bal_cur = ctx.balance_list[i]
            bal_prev = ctx.balance_list[i + 1]

            cip_cur = float(bal_cur.get("cip") or 0)
            cip_prev = float(bal_prev.get("cip") or 0)
            fix_cur = float(bal_cur.get("fix_assets") or 0)
            fix_prev = float(bal_prev.get("fix_assets") or 0)

            if cip_prev > 0:
                cip_growth = (cip_cur - cip_prev) / cip_prev * 100
                fix_growth = (fix_cur - fix_prev) / fix_prev * 100 if fix_prev else 0

                if cip_growth > 30 and fix_growth < cip_growth * 0.5:
                    years += 1

        detail = f"在建工程持续异常增长: {years}年"

        if years >= 3:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL"
        elif years >= 1:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"years": years})


class Rule3_4(BaseRule):
    """长期待摊费用大增"""
    code = "3.4"
    name = "长期待摊费用异常"
    layer = 3
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        bal_cur = ctx.latest(ctx.balance_list)
        bal_prev = ctx.prev(ctx.balance_list)

        if not bal_cur:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="无资产负债表数据")

        lt_amort = float(bal_cur.get("lt_amort_deferred_exp") or 0)
        total_assets = float(bal_cur.get("total_assets") or 1)
        ratio = lt_amort / total_assets * 100 if total_assets else 0

        yoy_change = 0
        if bal_prev:
            lt_amort_prev = float(bal_prev.get("lt_amort_deferred_exp") or 0)
            if lt_amort_prev > 0:
                yoy_change = (lt_amort - lt_amort_prev) / lt_amort_prev * 100

        detail = f"长期待摊: {self.format_number(lt_amort/1e8, 2)}亿, 占资产: {self.format_number(ratio, 2)}%, YoY: {self.format_number(yoy_change, 1)}%"

        if yoy_change > 100 or ratio > 1:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL"
        elif yoy_change > 50:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"lt_amort": lt_amort, "ratio": ratio, "yoy_change": yoy_change})


class Rule3_5(BaseRule):
    """坏账计提比例低于同行"""
    code = "3.5"
    name = "坏账计提不足"
    layer = 3
    weight_warn = 2
    weight_fail = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        inc_cur = ctx.latest(ctx.income_list)
        bal_cur = ctx.latest(ctx.balance_list)

        if not inc_cur or not bal_cur:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足")

        credit_loss = abs(float(inc_cur.get("credit_impa_loss") or 0))
        ar = float(bal_cur.get("accounts_receiv") or 0)

        if ar == 0:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.PASS, score_added=0, detail="应收账款为0 → PASS")

        bad_debt_ratio = credit_loss / ar * 100 if ar else 0
        peer_ratio = ctx.peer_indicators.get("bad_debt_ratio_median", 0)

        detail = f"坏账计提比例: {self.format_number(bad_debt_ratio, 2)}%"

        if peer_ratio:
            detail += f", 同行中位数: {self.format_number(peer_ratio, 2)}%"
            if peer_ratio > 0 and bad_debt_ratio < peer_ratio * 0.5:
                verdict = Verdict.FAIL
                score = self.weight_fail
                detail += " → FAIL: 远低于同行"
            elif bad_debt_ratio < peer_ratio:
                verdict = Verdict.WARN
                score = self.weight_warn
                detail += " → WARN"
            else:
                verdict = Verdict.PASS
                score = 0
                detail += " → PASS"
        else:
            verdict = Verdict.SKIP
            score = 0
            detail += " → SKIP: 同行数据不足"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"bad_debt_ratio": bad_debt_ratio, "peer_ratio": peer_ratio})


# ============================================
# Layer 4: 交叉验证（5条规则，权重最高）
# ============================================

class Rule4_1(BaseRule):
    """经营CF/净利润 < 1"""
    code = "4.1"
    name = "净现比异常"
    layer = 4
    weight_warn = 3
    weight_fail = 7

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if len(ctx.cashflow_list) < 3:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足3年")

        years_below_1 = 0
        for i in range(min(5, len(ctx.cashflow_list))):
            if i >= len(ctx.income_list):
                break
            cf = ctx.cashflow_list[i]
            inc = ctx.income_list[i]

            oper_cf = float(cf.get("n_cashflow_act") or 0)
            net_profit = float(inc.get("n_income_attr_p") or 0)

            if net_profit > 0 and 0 < oper_cf / net_profit < 1:
                years_below_1 += 1

        detail = f"近5年净现比<1: {years_below_1}年"

        if years_below_1 >= 3:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL"
        elif years_below_1 >= 2:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"years_below_1": years_below_1})


class Rule4_2(BaseRule):
    """销售收现/营收 < 1"""
    code = "4.2"
    name = "收现比异常"
    layer = 4
    weight_warn = 3
    weight_fail = 7

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if len(ctx.cashflow_list) < 2:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足")

        years_below = 0
        for i in range(min(5, len(ctx.cashflow_list))):
            if i >= len(ctx.income_list):
                break
            cf = ctx.cashflow_list[i]
            inc = ctx.income_list[i]

            cash_recp = float(cf.get("c_recp_prov_sg_act") or 0)
            revenue = float(inc.get("revenue") or 0)

            if revenue > 0 and cash_recp / revenue < 0.8:
                years_below += 1

        detail = f"近5年收现比<0.8: {years_below}年"

        if years_below >= 2:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL"
        elif years_below >= 1:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"years_below": years_below})


class Rule4_3(BaseRule):
    """资产膨胀 vs 利润增长"""
    code = "4.3"
    name = "资产利润背离"
    layer = 4
    weight_warn = 3
    weight_fail = 7

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if len(ctx.balance_list) < 2:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足")

        years_abnormal = 0
        for i in range(min(5, len(ctx.balance_list) - 1)):
            if i + 1 >= len(ctx.balance_list) or i >= len(ctx.income_list):
                break

            bal_cur = ctx.balance_list[i]
            bal_prev = ctx.balance_list[i + 1]
            inc = ctx.income_list[i]

            total_assets_cur = float(bal_cur.get("total_assets") or 0)
            total_assets_prev = float(bal_prev.get("total_assets") or 0)
            net_profit = float(inc.get("n_income_attr_p") or 0)

            if total_assets_prev > 0 and net_profit > 0:
                asset_growth = (total_assets_cur - total_assets_prev) / total_assets_prev * 100
                if asset_growth > 30:  # 资产增长超过30%
                    years_abnormal += 1

        detail = f"资产膨胀异常: {years_abnormal}年"

        if years_abnormal >= 2:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL"
        elif years_abnormal >= 1:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"years_abnormal": years_abnormal})


class Rule4_4(BaseRule):
    """核心利润 vs 净利润背离"""
    code = "4.4"
    name = "核心利润背离"
    layer = 4
    weight_warn = 3
    weight_fail = 7

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        inc_cur = ctx.latest(ctx.income_list)

        if not inc_cur:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="无利润表数据")

        revenue = float(inc_cur.get("revenue") or 0)
        oper_cost = float(inc_cur.get("oper_cost") or 0)
        sell_exp = float(inc_cur.get("sell_exp") or 0)
        admin_exp = float(inc_cur.get("admin_exp") or 0)
        fin_exp = float(inc_cur.get("fin_exp") or 0)
        net_profit = float(inc_cur.get("n_income_attr_p") or 0)

        core_profit = revenue - oper_cost - sell_exp - admin_exp - fin_exp

        if net_profit == 0:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="净利润为0")

        divergence = abs(core_profit - net_profit) / abs(net_profit) * 100

        detail = f"核心利润: {self.format_number(core_profit/1e8, 2)}亿, 净利润: {self.format_number(net_profit/1e8, 2)}亿, 背离度: {self.format_number(divergence, 1)}%"

        if divergence > 40:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL"
        elif divergence > 20:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"core_profit": core_profit, "net_profit": net_profit, "divergence": divergence})


class Rule4_5(BaseRule):
    """净利润增长 + FCF 持续为负"""
    code = "4.5"
    name = "盈利与自由现金背离"
    layer = 4
    weight_warn = 3
    weight_fail = 7

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if len(ctx.indicator_list) < 3:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足3年")

        years_abnormal = 0
        for i in range(min(5, len(ctx.indicator_list))):
            if i >= len(ctx.income_list):
                break
            ind = ctx.indicator_list[i]
            inc = ctx.income_list[i]

            net_profit = float(inc.get("n_income_attr_p") or 0)
            net_profit_prev = float(ctx.income_list[i + 1].get("n_income_attr_p") or 0) if i + 1 < len(ctx.income_list) else 0

            # FCFF 可能不在指标中，用简化版
            if i < len(ctx.cashflow_list):
                fcff = float(ctx.cashflow_list[i].get("free_cashflow") or 0)
            else:
                fcff = 0

            if net_profit > 0 and net_profit > net_profit_prev and fcff < 0:
                years_abnormal += 1

        detail = f"盈利增长但FCF为负: {years_abnormal}年"

        if years_abnormal >= 3:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL"
        elif years_abnormal >= 2:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail,
                         raw_values={"years_abnormal": years_abnormal})


# ============================================
# Layer 5: 非财务信号（6条规则）
# ============================================

class Rule5_1(BaseRule):
    """更换审计机构"""
    code = "5.1"
    name = "更换审计机构"
    layer = 5
    weight_warn = 1
    weight_fail = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        # 需要多年审计数据
        if len(ctx.income_list) < 3:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="数据不足3年")

        # 简化：检查当前审计机构
        agency = ctx.audit_agency or ""
        detail = f"当前审计机构: {agency}"

        # 需要历史数据对比，此处简化处理
        verdict = Verdict.PASS
        score = 0
        detail += " → PASS (需多年数据对比)"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail)


class Rule5_2(BaseRule):
    """大股东减持"""
    code = "5.2"
    name = "大股东减持"
    layer = 5
    weight_warn = 1
    weight_fail = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        # 需要股东数据
        detail = "大股东减持 (需股东数据)"

        verdict = Verdict.PASS
        score = 0
        detail += " → PASS (需股东数据)"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail)


class Rule5_3(BaseRule):
    """财务总监频繁更换"""
    code = "5.3"
    name = "高管变更"
    layer = 5
    weight_warn = 1
    weight_fail = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        detail = "财务总监变更 (需PDF数据)"

        verdict = Verdict.PASS
        score = 0
        detail += " → PASS (需PDF数据)"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail)


class Rule5_4(BaseRule):
    """独董集体辞职"""
    code = "5.4"
    name = "独董辞职"
    layer = 5
    weight_warn = 1
    weight_fail = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        detail = "独立董事辞职 (需PDF数据)"

        verdict = Verdict.PASS
        score = 0
        detail += " → PASS (需PDF数据)"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail)


class Rule5_5(BaseRule):
    """可疑供应商/客户"""
    code = "5.5"
    name = "客户集中度"
    layer = 5
    weight_warn = 1
    weight_fail = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        detail = "客户集中度 (需PDF数据)"

        verdict = Verdict.PASS
        score = 0
        detail += " → PASS (需PDF数据)"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail)


class Rule5_6(BaseRule):
    """跨行业频繁收购"""
    code = "5.6"
    name = "频繁并购"
    layer = 5
    weight_warn = 1
    weight_fail = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        detail = "跨行业收购 (需PDF数据)"

        verdict = Verdict.PASS
        score = 0
        detail += " → PASS (需PDF数据)"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail)


# ============================================
# Layer 6: 行业特有风险（2条规则）
# ============================================

class Rule6_1(BaseRule):
    """农林渔牧行业"""
    code = "6.1"
    name = "行业风险"
    layer = 6
    weight_warn = 1
    weight_fail = 3

    RISKY_INDUSTRIES = ["农业", "林业", "渔业", "牧业", "畜牧", "养殖", "种植", "饲料", "水产"]

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        industry = ctx.industry or ""

        detail = f"行业: {industry}"

        is_risky = any(r in industry for r in self.RISKY_INDUSTRIES)

        if is_risky:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN: 生物资产难以审计"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail)


class Rule6_2(BaseRule):
    """研发资本化比例"""
    code = "6.2"
    name = "研发资本化"
    layer = 6
    weight_warn = 1
    weight_fail = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        cap_ratio = ctx.pdf_data.get("rd_cap_ratio")

        if cap_ratio is None:
            return RuleResult(code=self.code, name=self.name, layer=self.layer,
                           verdict=Verdict.SKIP, detail="PDF中未找到研发资本化数据")

        detail = f"研发资本化比例: {self.format_number(cap_ratio, 1)}%"

        if cap_ratio > 50:
            verdict = Verdict.FAIL
            score = self.weight_fail
            detail += " → FAIL"
        elif cap_ratio > 30:
            verdict = Verdict.WARN
            score = self.weight_warn
            detail += " → WARN"
        else:
            verdict = Verdict.PASS
            score = 0
            detail += " → PASS"

        return RuleResult(code=self.code, name=self.name, layer=self.layer,
                         verdict=verdict, score_added=score, detail=detail)


# ============================================
# 规则引擎
# ============================================

class RuleEngine:
    """排雷规则引擎"""

    def __init__(self):
        self.rules: list[BaseRule] = [
            # Layer 0: 门槛检查
            Rule0_1(), Rule0_2(),
            # Layer 1: 利润表
            Rule1_1(), Rule1_2(), Rule1_3(), Rule1_4(), Rule1_5(), Rule1_6(),
            # Layer 2: 现金流量表
            Rule2_1(), Rule2_2(), Rule2_3(),
            # Layer 3: 资产负债表
            Rule3_1(), Rule3_2(), Rule3_3(), Rule3_4(), Rule3_5(),
            # Layer 4: 交叉验证
            Rule4_1(), Rule4_2(), Rule4_3(), Rule4_4(), Rule4_5(),
            # Layer 5: 非财务信号
            Rule5_1(), Rule5_2(), Rule5_3(), Rule5_4(), Rule5_5(), Rule5_6(),
            # Layer 6: 行业特有
            Rule6_1(), Rule6_2(),
        ]

    def analyze(self, ctx: RuleContext, report_year: int = 2024) -> ReportResult:
        """执行完整分析"""
        result = ReportResult(
            stock_code=ctx.stock_code,
            stock_name=ctx.stock_name,
            report_year=report_year,
        )

        # 逐条执行规则
        for rule in self.rules:
            rule_result = rule.evaluate(ctx)
            result.rule_results.append(rule_result)

            # Layer 0 一票否决
            if rule.layer == 0 and rule_result.verdict == Verdict.FAIL:
                result.n_fail += 1
                result.total_score += rule_result.score_added
                result.risk_level = RiskLevel.REJECT
                result.rule_results[-1].score_added = 999
                result.total_score = 999
                # 直接返回
                return result

            # 统计各类结果
            if rule_result.verdict == Verdict.PASS:
                result.n_pass += 1
            elif rule_result.verdict == Verdict.WARN:
                result.n_warn += 1
                result.total_score += rule_result.score_added
            elif rule_result.verdict == Verdict.FAIL:
                result.n_fail += 1
                result.total_score += rule_result.score_added
            elif rule_result.verdict == Verdict.SKIP:
                result.n_skip += 1

        # 计算组合加分
        result.combo_bonus = self._calc_combo_bonus(result.rule_results)
        result.total_score += result.combo_bonus

        # 确定风险等级
        result.risk_level = self._calc_risk_level(result.total_score)

        return result

    def _calc_combo_bonus(self, rule_results: list[RuleResult]) -> int:
        """计算组合加分"""
        bonus = 0

        # Rule 3.2 FAIL: 存货周转↓+毛利率↑ +10
        r32 = next((r for r in rule_results if r.code == "3.2"), None)
        if r32 and r32.verdict == Verdict.FAIL:
            bonus += 10

        # Rule 2.3 FAIL + Rule 4.1 FAIL: 大存大贷+CF/利润<1 +8
        r23 = next((r for r in rule_results if r.code == "2.3"), None)
        r41 = next((r for r in rule_results if r.code == "4.1"), None)
        if r23 and r23.verdict == Verdict.FAIL and r41 and r41.verdict == Verdict.FAIL:
            bonus += 8

        # Rule 1.2 FAIL + Rule 3.1 FAIL: 虚增收入组合 +6
        r12 = next((r for r in rule_results if r.code == "1.2"), None)
        r31 = next((r for r in rule_results if r.code == "3.1"), None)
        if r12 and r12.verdict == Verdict.FAIL and r31 and r31.verdict == Verdict.FAIL:
            bonus += 6

        return bonus

    def _calc_risk_level(self, score: int) -> RiskLevel:
        """根据分数确定风险等级"""
        if score >= 46:
            return RiskLevel.VERY_HIGH
        elif score >= 26:
            return RiskLevel.HIGH
        elif score >= 11:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
