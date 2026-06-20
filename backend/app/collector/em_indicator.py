"""财务指标采集器。

首选:
  - 同花顺摘要 stock_financial_abstract_ths(indicator='按报告期')
    - 提供: 销售净利率、销售毛利率、净资产收益率(ROE)、资产负债率、
      流动比率、速动比率、营业周期、存货周转率、应收账款周转天数等
  - 新浪三表自算指标 (as fallback):
    - roa, revenue_yoy, net_profit_yoy, cf_to_net_profit, sales_cash_ratio,
      总资产周转率, 应付账款周转率, ap_turnover

所有结果写入 fin_indicators 表，按 stock_code + report_date 唯一键 upsert。
"""
from __future__ import annotations

import pandas as pd
import akshare as ak
from decimal import Decimal

from app.db import db_session
from app.models import FinIndicator, BalanceSheet, IncomeStatement, CashFlow
from .base import BaseCollector, FetchError


# 同花顺映射 (symbol='600519', indicator='按报告期')
_THS_MAP = {
    "roe": "净资产收益率",
    "net_margin": "销售净利率",
    "debt_to_assets": "资产负债率",
    "current_ratio": "流动比率",
    "quick_ratio": "速动比率",
    "inventory_turnover": "存货周转率",
    "operating_cycle": "营业周期",
}


class THSIndicatorCollector(BaseCollector):
    """同花顺摘要指标 + 新浪三表自算指标。"""

    def __init__(self):
        super().__init__("ths_indicator")

    def _fetch(self, stock_code: str) -> pd.DataFrame:
        base = stock_code.split(".")[0]
        df = ak.stock_financial_abstract_ths(symbol=base, indicator="按报告期")
        if df is None or len(df) == 0:
            raise RuntimeError(f"stock_financial_abstract_ths 返回空: {base}")
        if "报告期" in df.columns:
            df["报告期"] = pd.to_datetime(df["报告期"], errors="coerce").dt.date
        return df

    def collect(self, stock_code: str) -> int:
        """写入 fin_indicators 并按 report_type 归类。返回写入记录数。"""
        try:
            df_ths = self.fetch(stock_code)
        except FetchError:
            self.log.warning("[%s] THS 指标不可达，仅使用三表自算", stock_code)
            df_ths = None

        # 读取三表数据
        with db_session() as session:
            bs_rows = [
                (r.report_date, r.report_type,
                 {"total_assets": r.total_assets, "inventory": r.inventory,
                  "accounts_payable": r.accounts_payable})
                for r in session.query(BalanceSheet)
                .filter(BalanceSheet.stock_code == stock_code)
                .order_by(BalanceSheet.report_date)
            ]
            inc_rows = [
                (r.report_date, r.report_type,
                 {"total_revenue": r.total_revenue, "net_profit": r.net_profit,
                  "net_profit_parent": r.net_profit_parent,
                  "operating_profit": r.operating_profit,
                  "gross_margin": r.gross_margin,
                  "financial_expenses": r.financial_expenses,
                  "selling_expenses": r.selling_expenses,
                  "admin_expenses": r.admin_expenses,
                  "rd_expenses": r.rd_expenses})
                for r in session.query(IncomeStatement)
                .filter(IncomeStatement.stock_code == stock_code)
                .order_by(IncomeStatement.report_date)
            ]
            cf_rows = [
                (r.report_date, r.report_type,
                 {"operating_cash_net": r.operating_cash_net,
                  "sales_cash_received": r.sales_cash_received})
                for r in session.query(CashFlow)
                .filter(CashFlow.stock_code == stock_code)
                .order_by(CashFlow.report_date)
            ]

        # 建立按 report_date 的索引
        def _index(rows):
            out = {}
            for d, t, v in rows:
                out[d] = (t, v)
            return out

        bs_map, inc_map, cf_map = _index(bs_rows), _index(inc_rows), _index(cf_rows)
        all_dates = sorted(set(bs_map) | set(inc_map) | set(cf_map))
        if not all_dates:
            self.log.info("[%s] 三表无数据，跳过指标计算", stock_code)
            return 0

        # 指标缓存
        ths_lookup = {}
        if df_ths is not None:
            for _, row in df_ths.iterrows():
                d = self.to_date(row["报告期"])
                if not d:
                    continue
                rec = {}
                for field, col in _THS_MAP.items():
                    v = self.to_decimal(row.get(col))
                    if v is not None:
                        rec[field] = v
                # 特殊: ar_turnover 需从周转天数换算(如存在)
                ar_days = self.to_decimal(row.get("应收账款周转天数"))
                if ar_days is not None and ar_days != 0:
                    rec["ar_turnover"] = Decimal("360") / ar_days
                ths_lookup[d] = rec

        written = 0
        with db_session() as session:
            for d in all_dates:
                report_type = (bs_map.get(d, (None, {}))[0]
                               or inc_map.get(d, (None, {}))[0]
                               or cf_map.get(d, (None, {}))[0])
                obj = (
                    session.query(FinIndicator)
                    .filter(FinIndicator.stock_code == stock_code,
                            FinIndicator.report_date == d)
                    .first()
                )
                if obj is None:
                    obj = FinIndicator(stock_code=stock_code, report_date=d,
                                       report_type=report_type or "")
                    session.add(obj)
                else:
                    if report_type:
                        obj.report_type = report_type

                vals = {}
                # 1) 来自 THS
                if d in ths_lookup:
                    vals.update(ths_lookup[d])

                # 2) 自算: ROA = net_profit_parent / total_assets
                bs_v = bs_map.get(d, (None, {}))[1] if d in bs_map else {}
                inc_v = inc_map.get(d, (None, {}))[1] if d in inc_map else {}
                cf_v = cf_map.get(d, (None, {}))[1] if d in cf_map else {}

                ta = bs_v.get("total_assets")
                np_parent = inc_v.get("net_profit_parent") or inc_v.get("net_profit")
                if ta and np_parent and ta != 0:
                    vals["roa"] = np_parent * Decimal("100") / ta

                # revenue_yoy / net_profit_yoy: 找上年同期
                prev_d = _year_before(d)
                prev_inc = inc_map.get(prev_d, (None, {}))[1] if prev_d in inc_map else {}
                if prev_inc:
                    cur_rev = inc_v.get("total_revenue")
                    prev_rev = prev_inc.get("total_revenue")
                    if cur_rev and prev_rev and prev_rev != 0:
                        vals["revenue_yoy"] = (cur_rev - prev_rev) * Decimal("100") / prev_rev
                    cur_np = np_parent
                    prev_np = prev_inc.get("net_profit_parent") or prev_inc.get("net_profit")
                    if cur_np and prev_np and prev_np != 0:
                        vals["net_profit_yoy"] = (cur_np - prev_np) * Decimal("100") / prev_np

                # cf_to_net_profit, sales_cash_ratio
                cf_net = cf_v.get("operating_cash_net")
                sales_cash = cf_v.get("sales_cash_received")
                rev = inc_v.get("total_revenue")
                np_for_cf = np_parent or inc_v.get("net_profit")
                if cf_net and np_for_cf and np_for_cf != 0:
                    vals["cf_to_net_profit"] = cf_net * Decimal("100") / np_for_cf
                if sales_cash and rev and rev != 0:
                    vals["sales_cash_ratio"] = sales_cash * Decimal("100") / rev

                # total_asset_turnover (simple: 当期营收/总资产)
                if rev and ta and ta != 0:
                    vals["total_asset_turnover"] = rev / ta

                # 写回对象
                for field, value in vals.items():
                    if value is not None:
                        setattr(obj, field, value)
                written += 1
            session.commit()

        self.log.info("[%s] 指标写入 %d 条", stock_code, written)
        return written


def _year_before(d):
    return d.replace(year=d.year - 1)


def collect_indicators(stock_code: str) -> int:
    return THSIndicatorCollector().collect(stock_code)
