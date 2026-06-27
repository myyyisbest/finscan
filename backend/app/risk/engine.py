"""finscan 风险排雷引擎。

规则使用注册器模式：每条规则 = 一个实现类 + @register_rule 装饰器。
规则阈值从 risk_rules 表读取，计算逻辑在代码里（诚实表述）。
使用说明:
    engine = RiskEngine(db_session)
    report = engine.evaluate("600519.SH", date(2025, 12, 31))
    db_session.add(report)
    db_session.commit()
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import json, logging
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.db import db_session as _default_db_session
from app.models import (
    RiskReport, RiskRuleResult, StockBasic,
)


logger = logging.getLogger("risk_engine")


# ===================== 数据结构 =====================

class RuleResult(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class RuleOutput:
    rule_code: str
    result: RuleResult
    score: Decimal
    evidence: str

    @classmethod
    def pass_result(cls, code: str) -> "RuleOutput":
        return cls(rule_code=code, result=RuleResult.PASS, score=Decimal("0"), evidence="")

    @classmethod
    def skip_result(cls, code: str, reason: str) -> "RuleOutput":
        return cls(rule_code=code, result=RuleResult.SKIP, score=Decimal("0"), evidence=f"SKIP: {reason}")

    @classmethod
    def warn(cls, code: str, score: Decimal, evidence: str) -> "RuleOutput":
        return cls(rule_code=code, result=RuleResult.WARN, score=score, evidence=evidence)

    @classmethod
    def fail(cls, code: str, score: Decimal, evidence: str) -> "RuleOutput":
        return cls(rule_code=code, result=RuleResult.FAIL, score=score, evidence=evidence)


# ===================== 规则注册器 =====================

_RULES: dict[str, type["BaseRule"]] = {}


def register_rule(code: str) -> Callable:
    """装饰器：将规则实现类注册到全局注册表。"""
    def deco(cls: type["BaseRule"]) -> type["BaseRule"]:
        _RULES[code] = cls
        cls.rule_code = code
        return cls
    return deco


def get_rule_class(code: str) -> type["BaseRule"] | None:
    return _RULES.get(code)


def all_rule_codes() -> list[str]:
    return list(_RULES.keys())


# ===================== 基类 =====================

@dataclass
class FinancialContext:
    """某公司某报告期周边的财务数据（多期，用于同比计算）。"""
    stock_code: str
    report_date: date
    bs: dict[str, Decimal | None]
    inc: dict[str, Decimal | None]
    cf: dict[str, Decimal | None]
    ind: dict[str, Decimal | None]
    # 历史数据（同最近N期）
    bs_history: list[dict[str, Decimal | None]] = field(default_factory=list)
    inc_history: list[dict[str, Decimal | None]] = field(default_factory=list)
    cf_history: list[dict[str, Decimal | None]] = field(default_factory=list)
    ind_history: list[dict[str, Decimal | None]] = field(default_factory=list)

    def get_prev(self, n: int = 1, which: str = "inc") -> dict:
        hist = getattr(self, f"{which}_history", [])
        idx = min(n, len(hist))
        return hist[idx - 1] if hist and idx > 0 else {}

    def get_prev_ind(self, n: int = 1) -> dict:
        """历史指标（含从三表补充的字段）。"""
        ind_hist = getattr(self, "ind_history", [])
        inc_hist = getattr(self, "inc_history", [])
        bs_hist = getattr(self, "bs_history", [])
        idx = min(n, len(ind_hist))
        if ind_hist and idx > 0:
            merged = dict(ind_hist[idx - 1])
            if inc_hist and idx <= len(inc_hist):
                inc = inc_hist[idx - 1]
                for k in ["gross_margin", "operating_profit", "investment_income",
                          "other_income", "financial_expenses",
                          "selling_expenses", "admin_expenses", "rd_expenses"]:
                    if k in inc and k not in merged:
                        merged[k] = inc[k]
            if bs_hist and idx <= len(bs_hist):
                bs = bs_hist[idx - 1]
                for k in ["goodwill", "other_receivables", "total_equity"]:
                    if k in bs and k not in merged:
                        merged[k] = bs[k]
            return merged
        return {}


class BaseRule(ABC):
    rule_code: str = ""

    @abstractmethod
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        """执行规则判定，返回 RuleOutput。"""
        ...

    def _delta_pct(self, cur, prev, default=None) -> Decimal | None:
        if cur is None or prev is None or prev == 0:
            return default
        return (cur - prev) * Decimal("100") / abs(prev)

    def _safe(self, d: dict, key: str) -> Decimal | None:
        v = d.get(key)
        return v if isinstance(v, Decimal) else None


# ===================== 具体规则实现 =====================

# ---- Layer 0: 硬性排除 ----

@register_rule("0.2")
class Rule_0_2(BaseRule):
    """年报按时披露：超4月30日未披露年报直接FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        if ctx.report_date.month != 12 or ctx.report_date.day == 31:
            return RuleOutput.pass_result(self.rule_code)
        cutoff = date(ctx.report_date.year, 4, 30)
        # 非年报跳过
        if ctx.report_date.month != 12:
            return RuleOutput.skip_result(self.rule_code, "非年报")
        # 此规则只对年报生效，数据库本身保证了年报有数据
        return RuleOutput.pass_result(self.rule_code)


# ---- Layer 1: 利润表异常 ----

@register_rule("1.1")
class Rule_1_1(BaseRule):
    """毛利率异常波动：同比变化>5pp WARN，>10pp FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        cur_gm = ctx.ind.get("gross_margin")  # 已是百分比值
        prev_ind = ctx.get_prev_ind(1)
        prev_gm = prev_ind.get("gross_margin")
        if cur_gm is None or prev_gm is None:
            return RuleOutput.skip_result(self.rule_code, "缺少毛利率数据")
        delta = abs(cur_gm - prev_gm)
        if delta > 10:
            return RuleOutput.fail(self.rule_code, Decimal("5"),
                f"毛利率同比变化 {delta:.2f}pp > 10pp (当前 {cur_gm:.2f}% vs 上期 {prev_gm:.2f}%)")
        if delta > 5:
            return RuleOutput.warn(self.rule_code, Decimal("2"),
                f"毛利率同比变化 {delta:.2f}pp > 5pp (当前 {cur_gm:.2f}% vs 上期 {prev_gm:.2f}%)")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("1.2")
class Rule_1_2(BaseRule):
    """毛利升 + 应收升 + 应付降：三项同时成立 FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        bs, inc = ctx.bs, ctx.inc
        bs_prev = ctx.get_prev(1, "bs")
        inc_prev = ctx.get_prev(1, "inc")
        if any(v is None for v in [
            bs.get("gross_profit"), bs_prev.get("gross_profit"),
            bs.get("accounts_receivable"), bs_prev.get("accounts_receivable"),
            bs.get("accounts_payable"), bs_prev.get("accounts_payable"),
        ]):
            return RuleOutput.skip_result(self.rule_code, "缺少相关科目数据")
        gm_up = (bs.get("gross_profit") or 0) > (bs_prev.get("gross_profit") or 0)
        ar_up = (bs.get("accounts_receivable") or 0) > (bs_prev.get("accounts_receivable") or 0)
        ap_down = (bs.get("accounts_payable") or 0) < (bs_prev.get("accounts_payable") or 0)
        if gm_up and ar_up and ap_down:
            return RuleOutput.fail(self.rule_code, Decimal("5"),
                f"毛利↑ + 应收↑ + 应付↓ 同时成立（虚增嫌疑）")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("1.4")
class Rule_1_4(BaseRule):
    """其他业务收入占比突增：>5% WARN，>15% FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        inc = ctx.inc
        prev_inc = ctx.get_prev(1, "inc")
        if inc.get("total_revenue") is None or prev_inc.get("total_revenue") is None:
            return RuleOutput.skip_result(self.rule_code, "缺少营收数据")
        # 新浪利润表不直接提供"其他业务收入"，使用投资净收益+其他收益作为代理
        other = (ctx.ind.get("other_income") or Decimal(0)) + (ctx.ind.get("investment_income") or Decimal(0))
        total = inc.get("total_revenue")
        if total == 0:
            return RuleOutput.skip_result(self.rule_code, "营收为0")
        ratio = other * Decimal("100") / abs(total)
        prev_other = (prev_inc.get("investment_income") or Decimal(0)) + (prev_inc.get("other_income") or Decimal(0))
        prev_total = prev_inc.get("total_revenue") or Decimal(1)
        prev_ratio = prev_other * Decimal("100") / abs(prev_total)
        if ratio > 15:
            return RuleOutput.fail(self.rule_code, Decimal("5"),
                f"其他收入占比 {ratio:.2f}% > 15%，同比+{ratio - prev_ratio:.2f}pp")
        if ratio > 5 and (ratio - prev_ratio) > 3:
            return RuleOutput.warn(self.rule_code, Decimal("2"),
                f"其他收入占比 {ratio:.2f}% > 5%，同比+{ratio - prev_ratio:.2f}pp > 3pp")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("1.5")
class Rule_1_5(BaseRule):
    """费用率异常下降：低于3年均值3pp WARN，5pp FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        # 费用率 = (销售+管理+研发+财务)/营收
        inc = ctx.inc
        total_rev = inc.get("total_revenue")
        if total_rev is None or total_rev == 0:
            return RuleOutput.skip_result(self.rule_code, "营收为空")
        cur_fee = sum(filter(None, [
            inc.get("selling_expenses"), inc.get("admin_expenses"),
            inc.get("rd_expenses"), inc.get("financial_expenses"),
        ])) or Decimal(0)
        cur_rate = cur_fee * Decimal("100") / abs(total_rev)
        # 3年均值
        vals = []
        for prev_inc in ctx.inc_history[:3]:
            rev = prev_inc.get("total_revenue")
            fee = sum(filter(None, [
                prev_inc.get("selling_expenses"), prev_inc.get("admin_expenses"),
                prev_inc.get("rd_expenses"), prev_inc.get("financial_expenses"),
            ]))
            if rev and rev != 0 and fee:
                vals.append(fee * Decimal("100") / abs(rev))
        if len(vals) < 2:
            return RuleOutput.skip_result(self.rule_code, "历史数据不足")
        avg = sum(vals) / Decimal(len(vals))
        diff = avg - cur_rate
        if diff > 5:
            return RuleOutput.fail(self.rule_code, Decimal("5"),
                f"费用率 {cur_rate:.2f}% 低于3年均值 {avg:.2f}% 共 {diff:.2f}pp > 5pp")
        if diff > 3:
            return RuleOutput.warn(self.rule_code, Decimal("2"),
                f"费用率 {cur_rate:.2f}% 低于3年均值 {avg:.2f}% 共 {diff:.2f}pp > 3pp")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("1.6")
class Rule_1_6(BaseRule):
    """资产减值损失暴增：同比>50% WARN，>100% FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        cur = ctx.inc.get("asset_impairment_loss")
        prev = ctx.get_prev(1, "inc").get("asset_impairment_loss")
        if cur is None or prev is None:
            return RuleOutput.skip_result(self.rule_code, "缺少减值数据")
        if prev == 0:
            return RuleOutput.skip_result(self.rule_code, "上期减值损失为0")
        delta = (cur - prev) * Decimal("100") / abs(prev)
        if delta > 100:
            return RuleOutput.fail(self.rule_code, Decimal("5"),
                f"资产减值损失同比+{delta:.1f}% > 100%")
        if delta > 50:
            return RuleOutput.warn(self.rule_code, Decimal("2"),
                f"资产减值损失同比+{delta:.1f}% > 50%")
        return RuleOutput.pass_result(self.rule_code)


# ---- Layer 2: 现金流异常 ----

@register_rule("2.1")
class Rule_2_1(BaseRule):
    """经营CF好 + 投资CF持续为负：投资CF > 经营CF的80% WARN，连续3年 FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        cur_cf = ctx.cf.get("operating_cash_net")
        cur_inv = ctx.cf.get("investing_cash_net")
        if cur_cf is None or cur_inv is None:
            return RuleOutput.skip_result(self.rule_code, "缺少现金流数据")
        if cur_cf <= 0:
            return RuleOutput.pass_result(self.rule_code)  # 经营CF本身不好，不适用
        if cur_inv >= -cur_cf * Decimal("0.8"):
            return RuleOutput.pass_result(self.rule_code)
        # 检查连续性
        consecutive = 1
        for prev_cf, prev_inv in zip(ctx.cf_history[1:], ctx.cf_history[1:]):
            if prev_cf is not None and prev_cf > 0 and prev_inv is not None and prev_inv < -prev_cf * Decimal("0.8"):
                consecutive += 1
            else:
                break
        if consecutive >= 3:
            return RuleOutput.fail(self.rule_code, Decimal("6"),
                f"投资现金持续净流出超经营现金80%达{consecutive}年")
        return RuleOutput.warn(self.rule_code, Decimal("3"),
            f"投资现金净流出超经营现金80%（当前{consecutive}年）")


@register_rule("2.2")
class Rule_2_2(BaseRule):
    """经营CF持续为负：近5年2年负 WARN，连续3年负 FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        seq = [(ctx.cf or {}).get("operating_cash_net")]
        for h in ctx.cf_history[:4]:
            seq.append(h.get("operating_cash_net"))
        neg_count = sum(1 for v in seq if v is not None and v < 0)
        if neg_count >= 3:
            return RuleOutput.fail(self.rule_code, Decimal("6"),
                f"经营现金流近5年中{neg_count}期为负 ≥ 3年")
        if neg_count >= 2:
            return RuleOutput.warn(self.rule_code, Decimal("3"),
                f"经营现金流近5年中{neg_count}期为负")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("2.3")
class Rule_2_3(BaseRule):
    """存贷双高：货币资金 > 有息负债 但财务费用率偏高 +2pp WARN，+4pp FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        bs = ctx.bs
        inc = ctx.inc
        monetary = bs.get("monetary_funds")
        st_borrow = bs.get("short_term_borrowings") or Decimal(0)
        lt_borrow = bs.get("long_term_borrowings") or Decimal(0)
        bonds = bs.get("bonds_payable") or Decimal(0)
        interest_debt = st_borrow + lt_borrow + bonds
        if monetary is None or interest_debt is None:
            return RuleOutput.skip_result(self.rule_code, "缺少货币资金或负债数据")
        if monetary <= interest_debt:
            return RuleOutput.pass_result(self.rule_code)
        rev = inc.get("total_revenue")
        fin_fee = inc.get("financial_expenses")
        if rev and rev != 0 and fin_fee is not None:
            rate = fin_fee * Decimal("100") / abs(rev)
            if rate > 4:
                return RuleOutput.fail(self.rule_code, Decimal("6"),
                    f"存贷双高：货币资金{int(monetary/1e8)}亿 > 有息负债{int(interest_debt/1e8)}亿，财务费用率{rate:.2f}% > 4%")
            if rate > 2:
                return RuleOutput.warn(self.rule_code, Decimal("3"),
                    f"存贷双高：货币资金{int(monetary/1e8)}亿 > 有息负债{int(interest_debt/1e8)}亿，财务费用率{rate:.2f}% > 2%")
        return RuleOutput.pass_result(self.rule_code)


# ---- Layer 3: 资产负债表异常 ----

@register_rule("3.1")
class Rule_3_1(BaseRule):
    """应收增速 > 营收增速：1.5倍 WARN，2倍 FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        ar_cur = ctx.bs.get("accounts_receivable")
        ar_prev = ctx.get_prev(1, "bs").get("accounts_receivable")
        rev_cur = ctx.inc.get("total_revenue")
        rev_prev = ctx.get_prev(1, "inc").get("total_revenue")
        if any(v is None for v in [ar_cur, ar_prev, rev_cur, rev_prev]):
            return RuleOutput.skip_result(self.rule_code, "缺少应收或营收数据")
        if ar_prev == 0 or rev_prev == 0:
            return RuleOutput.skip_result(self.rule_code, "上期基数为0")
        ar_growth = (ar_cur - ar_prev) * Decimal("100") / abs(ar_prev)
        rev_growth = (rev_cur - rev_prev) * Decimal("100") / abs(rev_prev)
        if rev_growth <= 0 and ar_growth > 0:
            ratio = abs(ar_growth / max(rev_growth, 0.001))
        elif rev_growth > 0:
            ratio = ar_growth / rev_growth
        else:
            return RuleOutput.pass_result(self.rule_code)
        if ratio >= 2:
            return RuleOutput.fail(self.rule_code, Decimal("5"),
                f"应收增速 {ar_growth:.1f}% / 营收增速 {rev_growth:.1f}% 比值 {ratio:.1f}x ≥ 2x")
        if ratio >= 1.5:
            return RuleOutput.warn(self.rule_code, Decimal("2"),
                f"应收增速 {ar_growth:.1f}% / 营收增速 {rev_growth:.1f}% 比值 {ratio:.1f}x ≥ 1.5x")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("3.2")
class Rule_3_2(BaseRule):
    """存货周转降 + 毛利率升：强烈背离 FAIL；接近 FAIL +10分组合。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        inv_t_cur = ctx.ind.get("inventory_turnover")
        gm_cur = ctx.ind.get("gross_margin")
        prev_ind = ctx.get_prev_ind(1)
        inv_t_prev = prev_ind.get("inventory_turnover")
        gm_prev = prev_ind.get("gross_margin")
        if any(v is None for v in [inv_t_cur, inv_t_prev, gm_cur, gm_prev]):
            return RuleOutput.skip_result(self.rule_code, "缺少存货周转或毛利率数据")
        if inv_t_prev == 0:
            return RuleOutput.skip_result(self.rule_code, "上期存货周转率为0")
        t_drop = (inv_t_prev - inv_t_cur) * Decimal("100") / inv_t_prev
        gm_up = gm_cur - gm_prev
        if t_drop > 10 and gm_up > 2:
            return RuleOutput.fail(self.rule_code, Decimal("5"),
                f"存货周转率下降 {t_drop:.1f}% > 10% 且毛利率上升 {gm_up:.2f}pp（积压+提价嫌疑）")
        if t_drop > 5 and gm_up > 1:
            return RuleOutput.warn(self.rule_code, Decimal("2"),
                f"存货周转率下降 {t_drop:.1f}% 且毛利率上升 {gm_up:.2f}pp")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("3.3")
class Rule_3_3(BaseRule):
    """在建工程不转固：增加>30%无固定资产增加 WARN，持续3年 FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        cip_cur = ctx.bs.get("construction_in_progress")
        fa_cur = ctx.bs.get("fixed_assets")
        if cip_cur is None:
            return RuleOutput.skip_result(self.rule_code, "缺少在建工程数据")
        # 上期 CIP
        prev_bs = ctx.get_prev(1, "bs")
        cip_prev = prev_bs.get("construction_in_progress")
        fa_prev = prev_bs.get("fixed_assets")
        if cip_prev is None or cip_cur is None:
            return RuleOutput.skip_result(self.rule_code, "缺少CIP历史数据")
        if cip_prev == 0:
            return RuleOutput.skip_result(self.rule_code, "上期CIP为0")
        cip_growth = (cip_cur - cip_prev) * Decimal("100") / cip_prev
        fa_growth = Decimal("0")
        if fa_prev and fa_prev != 0 and fa_cur is not None:
            fa_growth = (fa_cur - fa_prev) * Decimal("100") / abs(fa_prev)
        if cip_growth > 30 and fa_growth < 5:
            # 检查持续性
            consecutive = 1
            for h in ctx.bs_history[1:3]:
                c = h.get("construction_in_progress") or Decimal(0)
                p = h.get("fixed_assets") or Decimal(1)
                if c > 0:
                    g = (c - cip_prev) * Decimal("100") / abs(cip_prev) if cip_prev != 0 else Decimal(0)
                    if g > 30 and (p - fa_prev) * Decimal("100") / abs(fa_prev) < 5:
                        consecutive += 1
            if consecutive >= 3:
                return RuleOutput.fail(self.rule_code, Decimal("5"),
                    f"在建工程持续3年增加>30%但固定资产增加<5%（资本化嫌疑）")
            return RuleOutput.warn(self.rule_code, Decimal("2"),
                f"在建工程增加 {cip_growth:.1f}% > 30% 但固定资产仅 {fa_growth:.1f}%")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("3.4")
class Rule_3_4(BaseRule):
    """长期待摊费用大增：同比>50% WARN，>100% FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        cur = ctx.bs.get("long_deferred_expenses")
        prev = ctx.get_prev(1, "bs").get("long_deferred_expenses")
        if cur is None or prev is None:
            return RuleOutput.skip_result(self.rule_code, "缺少长期待摊数据")
        if prev == 0:
            return RuleOutput.skip_result(self.rule_code, "上期数据为0")
        delta = (cur - prev) * Decimal("100") / abs(prev)
        if delta > 100:
            return RuleOutput.fail(self.rule_code, Decimal("5"),
                f"长期待摊费用同比 {delta:.1f}% > 100%")
        if delta > 50:
            return RuleOutput.warn(self.rule_code, Decimal("2"),
                f"长期待摊费用同比 {delta:.1f}% > 50%")
        return RuleOutput.pass_result(self.rule_code)


# ---- Layer 4: 交叉验证 ----

@register_rule("4.1")
class Rule_4_1(BaseRule):
    """经营CF/净利润 < 1：近5年2年 WARN，连续3年 FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        seq = []
        all_cf = [(ctx.cf or {}).get("operating_cash_net")] + [h.get("operating_cash_net") for h in ctx.cf_history[:4]]
        all_np = [(ctx.inc or {}).get("net_profit_parent")] + [h.get("net_profit_parent") for h in ctx.inc_history[:4]]
        for cf, np_ in zip(all_cf, all_np):
            if cf is not None and np_ is not None and np_ > 0:
                seq.append(cf / np_)
        bad = sum(1 for r in seq if r < 1)
        if bad >= 3:
            return RuleOutput.fail(self.rule_code, Decimal("7"),
                f"经营CF/净利润<1 近5年出现{bad}次 ≥ 3次")
        if bad >= 2:
            return RuleOutput.warn(self.rule_code, Decimal("3"),
                f"经营CF/净利润<1 近5年出现{bad}次")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("4.2")
class Rule_4_2(BaseRule):
    """销售收现/营收 < 1：<0.9 WARN，<0.8持续2年 FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        cf = ctx.cf
        inc = ctx.inc
        if cf.get("sales_cash_received") is None or inc.get("total_revenue") is None:
            return RuleOutput.skip_result(self.rule_code, "缺少销售收现或营收数据")
        rev = inc.get("total_revenue")
        if rev == 0:
            return RuleOutput.skip_result(self.rule_code, "营收为0")
        ratio = cf.get("sales_cash_received") * Decimal("100") / abs(rev)
        if ratio < 80:
            prev_inc = ctx.get_prev(1, "inc")
            prev_cf = ctx.get_prev(1, "cf")
            if prev_cf and prev_inc:
                prev_rev = prev_inc.get("total_revenue")
                if prev_rev and prev_rev != 0:
                    prev_ratio = prev_cf.get("sales_cash_received", 0) * Decimal("100") / abs(prev_rev)
                    if prev_ratio < 80:
                        return RuleOutput.fail(self.rule_code, Decimal("7"),
                            f"销售收现比连续2年<80%")
            return RuleOutput.fail(self.rule_code, Decimal("7"),
                f"销售收现比 {ratio:.1f}% < 80%")
        if ratio < 90:
            return RuleOutput.warn(self.rule_code, Decimal("3"),
                f"销售收现比 {ratio:.1f}% < 90%")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("4.3")
class Rule_4_3(BaseRule):
    """利润膨胀 + 资产膨胀：净利润增速 > 营收增速 2倍 WARN，3倍 FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        inc = ctx.inc
        prev_inc = ctx.get_prev(1, "inc")
        bs = ctx.bs
        prev_bs = ctx.get_prev(1, "bs")
        if any(v is None for v in [
            inc.get("net_profit_parent"), prev_inc.get("net_profit_parent"),
            inc.get("total_revenue"), prev_inc.get("total_revenue"),
            bs.get("total_assets"), prev_bs.get("total_assets"),
        ]):
            return RuleOutput.skip_result(self.rule_code, "缺少增速数据")
        np_cur = inc.get("net_profit_parent")
        np_prev = prev_inc.get("net_profit_parent")
        rev_cur = inc.get("total_revenue")
        rev_prev = prev_inc.get("total_revenue")
        if np_prev == 0 or rev_prev == 0:
            return RuleOutput.skip_result(self.rule_code, "上期基数为0")
        np_growth = (np_cur - np_prev) * Decimal("100") / abs(np_prev)
        rev_growth = (rev_cur - rev_prev) * Decimal("100") / abs(rev_prev)
        if rev_growth <= 0:
            return RuleOutput.pass_result(self.rule_code)
        ratio = np_growth / rev_growth
        if ratio >= 3:
            return RuleOutput.fail(self.rule_code, Decimal("7"),
                f"净利润增速 {np_growth:.1f}% / 营收增速 {rev_growth:.1f}% 比值{ratio:.1f}x ≥ 3x")
        if ratio >= 2:
            return RuleOutput.warn(self.rule_code, Decimal("3"),
                f"净利润增速 {np_growth:.1f}% / 营收增速 {rev_growth:.1f}% 比值{ratio:.1f}x ≥ 2x")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("4.4")
class Rule_4_4(BaseRule):
    """核心利润与净利润背离：偏差>20% WARN，>40% FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        inc = ctx.inc
        core_profit = (inc.get("operating_profit") or Decimal(0)) + \
                      (inc.get("investment_income") or Decimal(0)) + \
                      (inc.get("other_income") or Decimal(0))
        np_ = inc.get("net_profit")
        if core_profit == 0 or np_ is None:
            return RuleOutput.skip_result(self.rule_code, "缺少利润数据")
        diff = abs(core_profit - np_) * Decimal("100") / abs(core_profit)
        if diff > 40:
            return RuleOutput.fail(self.rule_code, Decimal("7"),
                f"核心利润与净利润偏差 {diff:.1f}% > 40%")
        if diff > 20:
            return RuleOutput.warn(self.rule_code, Decimal("3"),
                f"核心利润与净利润偏差 {diff:.1f}% > 20%")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("4.5")
class Rule_4_5(BaseRule):
    """净利润增 + FCF持续负：2年负 WARN，3年负 FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        inc = ctx.inc
        prev_inc = ctx.get_prev(1, "inc")
        if inc.get("net_profit_parent") is None or prev_inc.get("net_profit_parent") is None:
            return RuleOutput.skip_result(self.rule_code, "缺少净利润数据")
        np_up = inc.get("net_profit_parent", 0) > prev_inc.get("net_profit_parent", 0)
        if not np_up:
            return RuleOutput.pass_result(self.rule_code)
        fcf_seq = [(ctx.cf or {}).get("free_cash_flow")] + \
                  [h.get("free_cash_flow") for h in ctx.cf_history[:4]]
        neg_count = sum(1 for v in fcf_seq if v is not None and v < 0)
        if neg_count >= 3:
            return RuleOutput.fail(self.rule_code, Decimal("7"),
                f"净利润增长但自由现金流{neg_count}期为负 ≥ 3年")
        if neg_count >= 2:
            return RuleOutput.warn(self.rule_code, Decimal("3"),
                f"净利润增长但自由现金流{neg_count}期为负")
        return RuleOutput.pass_result(self.rule_code)


# ---- Layer 5: 非财务异常 ----

@register_rule("5.7")
class Rule_5_7(BaseRule):
    """商誉占比过高：商誉/净资产 > 20% WARN，> 40% FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        goodwill = ctx.bs.get("goodwill")
        equity = ctx.bs.get("total_equity")
        if goodwill is None or equity is None or equity == 0:
            return RuleOutput.skip_result(self.rule_code, "缺少商誉或净资产数据")
        ratio = goodwill * Decimal("100") / abs(equity)
        if ratio > 40:
            return RuleOutput.fail(self.rule_code, Decimal("3"),
                f"商誉/净资产 {ratio:.2f}% > 40%")
        if ratio > 20:
            return RuleOutput.warn(self.rule_code, Decimal("1"),
                f"商誉/净资产 {ratio:.2f}% > 20%")
        return RuleOutput.pass_result(self.rule_code)


@register_rule("5.8")
class Rule_5_8(BaseRule):
    """其他应收款异常：占总资产>3% WARN，>5% FAIL；或同比>50% FAIL。"""
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        other = ctx.bs.get("other_receivables")
        assets = ctx.bs.get("total_assets")
        prev_bs = ctx.get_prev(1, "bs")
        prev_other = prev_bs.get("other_receivables")
        if other is None or assets is None or assets == 0:
            return RuleOutput.skip_result(self.rule_code, "缺少其他应收或总资产数据")
        ratio = other * Decimal("100") / abs(assets)
        if ratio > 5:
            return RuleOutput.fail(self.rule_code, Decimal("3"),
                f"其他应收款占总资产 {ratio:.2f}% > 5%")
        if ratio > 3:
            return RuleOutput.warn(self.rule_code, Decimal("1"),
                f"其他应收款占总资产 {ratio:.2f}% > 3%")
        if prev_other and prev_other != 0:
            growth = (other - prev_other) * Decimal("100") / abs(prev_other)
            if growth > 50:
                return RuleOutput.fail(self.rule_code, Decimal("3"),
                    f"其他应收款同比+{growth:.1f}% > 50%")
        return RuleOutput.pass_result(self.rule_code)


# ---- Layer 6: 行业风险 ----

@register_rule("6.1")
class Rule_6_1(BaseRule):
    """农林渔牧行业：自动 WARN。"""
    RISKY_INDUSTRIES = {"农林牧渔", "农林渔业"}
    def evaluate(self, ctx: FinancialContext) -> RuleOutput:
        # 行业信息从 StockBasic 获取，传参传入
        industry = getattr(ctx, "industry", None)
        if industry and industry in self.RISKY_INDUSTRIES:
            return RuleOutput.warn(self.rule_code, Decimal("1"),
                f"行业为「{industry}」，生物资产核查困难")
        return RuleOutput.pass_result(self.rule_code)


# ===================== 组合加分 =====================

_COMBO_BONUS: dict[frozenset, Decimal] = {
    frozenset(["3.2", "FAIL"]): Decimal("10"),   # 存货背离 FAIL +10
    frozenset(["2.3", "FAIL", "4.1", "FAIL"]): Decimal("8"),  # 存贷双高 + CF比
    frozenset(["1.2", "FAIL", "3.1", "FAIL"]): Decimal("6"),   # 毛利升应收升 + 应收增速
}


# ===================== 风险引擎 =====================

class RiskEngine:
    """风险排雷引擎主类。"""

    def __init__(self, session: Session):
        self.session = session

    def load_financial_data(self, stock_code: str, report_date: date, years: int = 6) -> FinancialContext:
        """从数据库加载指定报告期的财务数据（含历史序列）。优先使用 FinReport 模型。"""
        from app.models import FinReport
        stock_code = stock_code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
        start_year = report_date.year - years
        start_date = date(start_year, 1, 1)

        rows = (
            self.session.query(FinReport)
            .filter(
                FinReport.stock_code == stock_code,
                FinReport.report_date <= report_date,
                FinReport.report_date >= start_date,
            )
            .order_by(FinReport.report_date.desc())
            .all()
        )

        BS_MAP = {
            "TOTAL_ASSETS": "total_assets",
            "TOTAL_LIAB": "total_liabilities",
            "TOTAL_LIABILITIES": "total_liabilities",
            "TOTAL_EQUITY": "total_equity",
            "TOTAL_HLDEQ": "total_equity",
            "MONETARYFUNDS": "monetary_funds",
            "ACCOUNTS_RECE": "accounts_receivable",
            "ACCOUNTS_RECEIVABLE": "accounts_receivable",
            "OTHRECE": "other_receivables",
            "OTHER_RECEIVABLE": "other_receivables",
            "INVENTORY": "inventory",
            "GOODWILL": "goodwill",
            "FIXED_ASSET": "fixed_assets",
            "CIP": "construction_in_progress",
            "INTANGIBLE_ASSET": "intangible_assets",
            "LT_AMORT_DEFERRED_EXP": "long_deferred_expenses",
            "LONG_TERM_PAYROLL_PAYABLE": "long_deferred_expenses",
            "ST_BORR": "short_term_borrowings",
            "SHORT_BORROW": "short_term_borrowings",
            "LT_BORR": "long_term_borrowings",
            "LONG_BORROW": "long_term_borrowings",
            "BOND_PAYABLE": "bonds_payable",
            "ACCOUNTS_PAYABLE": "accounts_payable",
            "ADVANCE_RECEIPTS": "advance_receipts",
            "CONTRACT_LIAB": "contract_liab",
            "TOTAL_CURRENT_ASSETS": "total_current_assets",
            "CURRENT_ASSET_BALANCE": "total_current_assets",
            "TOTAL_CURRENT_LIAB": "total_current_liabilities",
            "CURRENT_LIAB_BALANCE": "total_current_liabilities",
        }

        INC_MAP = {
            "TOTAL_OPERATE_INCOME": "total_revenue",
            "OPERATE_INCOME": "total_revenue",
            "OPERATE_COST": "operating_cost",
            "OPERATING_COST": "operating_cost",
            "OPERATE_PROFIT": "operating_profit",
            "OPERATING_PROFIT": "operating_profit",
            "TOTAL_PROFIT": "total_profit",
            "NETPROFIT": "net_profit",
            "NET_PROFIT": "net_profit",
            "PARENT_NETPROFIT": "net_profit_parent",
            "DEDUCT_PARENT_NETPROFIT": "deduct_net_profit",
            "GROSS_PROFIT": "gross_profit",
            "SALE_EXPENSE": "selling_expenses",
            "SELL_EXP": "selling_expenses",
            "MANAGE_EXPENSE": "admin_expenses",
            "ADMIN_EXP": "admin_expenses",
            "RD_EXPENSE": "rd_expenses",
            "FINANCE_EXPENSE": "financial_expenses",
            "FIN_EXP": "financial_expenses",
            "ASSET_IMPAIRMENT_LOSS": "asset_impairment_loss",
            "IMPAIRMENT_LOSS_ASSET": "asset_impairment_loss",
            "INVEST_INCOME": "investment_income",
            "INVEST_INCOME_ASSIGN": "investment_income",
            "OTHER_INCOME": "other_income",
            "OTHER_BUSINESS_INCOME": "other_business_income",
            "BASIC_EPS": "basic_eps",
        }

        CF_MAP = {
            "NETCASH_OPERATE": "operating_cash_net",
            "OPERATE_NETCASH": "operating_cash_net",
            "NETCASH_INVEST": "investing_cash_net",
            "INVEST_NETCASH": "investing_cash_net",
            "NETCASH_FINANCE": "financing_cash_net",
            "FINANCE_NETCASH": "financing_cash_net",
            "SALES_SERVICES": "sales_cash_received",
            "RECEV_GOODS_SALE": "sales_cash_received",
            "CONSTRUCT_LONG_ASSET": "construct_long_asset",
            "CIP_CAPEX": "construct_long_asset",
            "FREE_CASHFLOW": "free_cash_flow",
            "FCFF": "free_cash_flow",
        }

        def _extract(json_data, field_map):
            result = {}
            for src_key, dst_key in field_map.items():
                v = json_data.get(src_key) if json_data else None
                if v is not None:
                    try:
                        result[dst_key] = Decimal(str(v))
                    except (ValueError, TypeError):
                        pass
            return result

        def _row_to_dicts(row):
            bs = _extract(row.balance_json, BS_MAP)
            inc = _extract(row.income_json, INC_MAP)
            cf = _extract(row.cashflow_json, CF_MAP)
            if row.total_assets and "total_assets" not in bs:
                bs["total_assets"] = row.total_assets
            if row.total_liabilities and "total_liabilities" not in bs:
                bs["total_liabilities"] = row.total_liabilities
            if row.total_equity and "total_equity" not in bs:
                bs["total_equity"] = row.total_equity
            if row.total_revenue and "total_revenue" not in inc:
                inc["total_revenue"] = row.total_revenue
            if row.operate_profit and "operating_profit" not in inc:
                inc["operating_profit"] = row.operate_profit
            if row.net_profit and "net_profit" not in inc:
                inc["net_profit"] = row.net_profit
            if row.net_profit_parent and "net_profit_parent" not in inc:
                inc["net_profit_parent"] = row.net_profit_parent
            if row.operate_cash_net and "operating_cash_net" not in cf:
                cf["operating_cash_net"] = row.operate_cash_net
            if row.gross_margin is not None:
                inc["gross_margin"] = row.gross_margin
            return bs, inc, cf

        all_dicts = [_row_to_dicts(r) for r in rows]

        cur_bs, cur_inc, cur_cf = {}, {}, {}
        cur_row = None
        for i, r in enumerate(rows):
            if r.report_date == report_date:
                cur_bs, cur_inc, cur_cf = all_dicts[i]
                cur_row = r
                break

        bs_history, inc_history, cf_history = [], [], []
        for i, r in enumerate(rows):
            if r.report_date == report_date:
                continue
            bs_history.append(all_dicts[i][0])
            inc_history.append(all_dicts[i][1])
            cf_history.append(all_dicts[i][2])

        cur_ind = {}
        if cur_row:
            if cur_row.roe is not None:
                cur_ind["roe"] = cur_row.roe
            if cur_row.roa is not None:
                cur_ind["roa"] = cur_row.roa
            if cur_row.gross_margin is not None:
                cur_ind["gross_margin"] = cur_row.gross_margin
            if cur_row.net_margin is not None:
                cur_ind["net_margin"] = cur_row.net_margin
            if cur_row.debt_ratio is not None:
                cur_ind["debt_ratio"] = cur_row.debt_ratio
            if cur_row.current_ratio is not None:
                cur_ind["current_ratio"] = cur_row.current_ratio
            if cur_row.quick_ratio is not None:
                cur_ind["quick_ratio"] = cur_row.quick_ratio
            if cur_row.revenue_yoy is not None:
                cur_ind["revenue_yoy"] = cur_row.revenue_yoy
            if cur_row.net_profit_yoy is not None:
                cur_ind["net_profit_yoy"] = cur_row.net_profit_yoy
            if cur_row.eps is not None:
                cur_ind["eps"] = cur_row.eps
            if cur_row.bps is not None:
                cur_ind["bps"] = cur_row.bps

        for key in ["operating_profit", "investment_income", "other_income",
                    "gross_margin", "financial_expenses",
                    "selling_expenses", "admin_expenses", "rd_expenses"]:
            if key in cur_inc and key not in cur_ind:
                cur_ind[key] = cur_inc[key]

        for key in ["goodwill", "other_receivables", "total_equity"]:
            if key in cur_bs and key not in cur_ind:
                cur_ind[key] = cur_bs[key]

        try:
            from app.models import FinMainIndicator
            ind_rows = (
                self.session.query(FinMainIndicator)
                .filter(
                    FinMainIndicator.stock_code == stock_code,
                    FinMainIndicator.report_date <= report_date,
                    FinMainIndicator.report_date >= start_date,
                )
                .order_by(FinMainIndicator.report_date.desc())
                .all()
            )
            for ind_row in ind_rows:
                if ind_row.report_date == report_date and ind_row.raw_json:
                    raw = ind_row.raw_json
                    for k in ["INVENTORY_TURN", "INV_TURN", "INVENTORY_TURNOVER"]:
                        if k in raw and raw[k] is not None:
                            try:
                                cur_ind["inventory_turnover"] = Decimal(str(raw[k]))
                            except (ValueError, TypeError):
                                pass
                            break
                    for k in ["AR_TURN", "RECEIVABLE_TURN", "AR_TURNOVER", "ACCOUNTS_RECE_TURN"]:
                        if k in raw and raw[k] is not None and "receivable_turnover" not in cur_ind:
                            try:
                                cur_ind["receivable_turnover"] = Decimal(str(raw[k]))
                            except (ValueError, TypeError):
                                pass
                            break
                    for k in ["ASSETS_TURN", "TOTAL_ASSET_TURN", "TOTAL_ASSETS_TURNOVER", "TAT"]:
                        if k in raw and raw[k] is not None and "total_asset_turnover" not in cur_ind:
                            try:
                                cur_ind["total_asset_turnover"] = Decimal(str(raw[k]))
                            except (ValueError, TypeError):
                                pass
                            break
        except Exception:
            pass

        return FinancialContext(
            stock_code=stock_code,
            report_date=report_date,
            bs=cur_bs, inc=cur_inc, cf=cur_cf, ind=cur_ind,
            bs_history=bs_history,
            inc_history=inc_history,
            cf_history=cf_history,
            ind_history=[],
        )

    def evaluate(self, stock_code: str, report_date: date, industry: str | None = None) -> RiskReport:
        """执行全套规则评估，返回 RiskReport。"""
        ctx = self.load_financial_data(stock_code, report_date)
        if industry:
            ctx.industry = industry  # 给 Rule 6.1 用

        total_score = Decimal("0")
        rule_count = 0
        participated = 0
        combo_keys: dict[str, str] = {}  # rule_code -> result

        outputs: list[RuleOutput] = []
        for code in sorted(all_rule_codes()):
            cls = get_rule_class(code)
            if cls is None:
                continue
            try:
                output = cls().evaluate(ctx)
            except Exception as exc:
                logger.warning("规则 %s 执行异常: %s", code, exc)
                output = RuleOutput.skip_result(code, f"执行异常: {exc}")

            outputs.append(output)
            if output.result in (RuleResult.WARN, RuleResult.FAIL):
                total_score += output.score
                participated += 1
            rule_count += 1
            combo_keys[code] = output.result.value

        # 组合加分
        for combo_key, bonus in _COMBO_BONUS.items():
            parts = list(combo_key)
            # parts: ["3.2", "FAIL", "4.1", "FAIL"] -> [(code,result), ...]
            match = True
            for i in range(0, len(parts), 2):
                code, result = parts[i], parts[i + 1]
                if combo_keys.get(code) != result:
                    match = False
                    break
            if match:
                total_score += bonus
                logger.info("组合加分: %s +%.0f", combo_key, bonus)

        # 风险等级
        if total_score >= 46:
            risk_level = "极高"
        elif total_score >= 26:
            risk_level = "高"
        elif total_score >= 11:
            risk_level = "中"
        else:
            risk_level = "低"

        # 数据完整度
        completeness = Decimal("0")
        for d in [ctx.bs, ctx.inc, ctx.cf, ctx.ind]:
            if d:
                completeness += Decimal("1")
        completeness = completeness * Decimal("25")

        report = RiskReport(
            stock_code=stock_code,
            report_date=report_date,
            total_score=total_score,
            risk_level=risk_level,
            rule_total=rule_count,
            rule_participated=participated,
            data_completeness=completeness,
            calc_time=datetime.now(),
        )

        # 写入明细（upsert）
        for out in outputs:
            existing = (
                self.session.query(RiskRuleResult)
                .filter(
                    RiskRuleResult.stock_code == stock_code,
                    RiskRuleResult.report_date == report_date,
                    RiskRuleResult.rule_code == out.rule_code,
                )
                .first()
            )
            if existing:
                existing.result = out.result.value
                existing.score = out.score
                existing.evidence = out.evidence
                existing.calc_time = datetime.now()
            else:
                result = RiskRuleResult(
                    stock_code=stock_code,
                    report_date=report_date,
                    rule_code=out.rule_code,
                    result=out.result.value,
                    score=out.score,
                    evidence=out.evidence,
                    calc_time=datetime.now(),
                )
                self.session.add(result)

        return report

    def batch_evaluate(self, stock_codes: list[str], report_date: date) -> list[RiskReport]:
        """批量评估多家公司。"""
        reports = []
        for code in stock_codes:
            try:
                report = self.evaluate(code, report_date)
                # upsert
                existing = self.session.query(RiskReport).filter(
                    RiskReport.stock_code == code,
                    RiskReport.report_date == report_date,
                ).first()
                if existing:
                    existing.total_score = report.total_score
                    existing.risk_level = report.risk_level
                    existing.rule_total = report.rule_total
                    existing.rule_participated = report.rule_participated
                    existing.data_completeness = report.data_completeness
                    existing.calc_time = report.calc_time
                else:
                    self.session.add(report)
                self.session.commit()
                reports.append(existing or report)
            except Exception as exc:  # noqa: BLE001
                logger.warning("批量排雷 %s 异常: %s", code, exc)
        return reports
