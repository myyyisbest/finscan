"""新浪『主要指标』采集 —— 来自 ak.stock_financial_analysis_indicator。

覆盖 EM 财务分析页 主要指标 80+ 字段 (每股 / 规模 / 成长 / 盈利 / 收益质量 / 偿债 / 营运)。
一份调用即获得近 6 年 (按 report_date 倒序) 全部季度数据。
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Iterable

import pandas as pd
import akshare as ak
from sqlalchemy.orm import Session

from app.db import db_session
from app.models import FinMainIndicator, StockBasic
from .base import BaseCollector

log = logging.getLogger(__name__)


# ===== 字段映射: 新浪列名 → 模型字段 =====
_COL_MAP = {
    # 每股
    "摊薄每股收益(元)": "eps_basic",
    "稀释每股收益(元)": "eps_diluted",
    "加权每股收益(元)": "eps_weighted",
    "每股收益_调整后(元)": "eps_adj",
    "扣除非经常性损益后的每股收益(元)": "eps_deduct",
    "每股净资产_调整前(元)": "bps",
    "每股净资产_调整后(元)": "bps_adj",
    "每股经营性现金流(元)": "ocfps",
    "每股资本公积金(元)": "capital_reserve_per_share",
    "每股未分配利润(元)": "retained_eps",
    # 规模
    "主营业务收入": "main_revenue",
    "主营业务利润(元)": "main_profit",
    "扣除非经常性损益后的净利润(元)": "net_profit_deduct",
    "总资产(元)": "total_assets",
    # 成长
    "主营业务收入增长率(%)": "revenue_yoy",
    "净利润增长率(%)": "net_profit_yoy",
    "净资产增长率(%)": "equity_yoy",
    "总资产增长率(%)": "total_asset_yoy",
    # 盈利
    "净资产收益率(%)": "roe",
    "加权净资产收益率(%)": "roe_weighted",
    "总资产利润率(%)": "roa",
    "总资产净利润率(%)": "roa_net",
    "销售净利率(%)": "net_margin",
    "销售毛利率(%)": "gross_margin",
    "主营业务利润率(%)": "main_profit_margin",
    "营业利润率(%)": "op_margin",
    "成本费用利润率(%)": "cost_to_expense_margin",
    "股息发放率(%)": "dividend_ratio",
    # 收益质量
    "经营现金净流量对销售收入比率(%)": "sales_cash_ratio",
    "资产的经营现金流量回报率(%)": "cf_to_assets",
    "经营现金净流量与净利润的比率(%)": "cf_to_net_profit",
    "经营现金净流量对负债比率(%)": "cf_to_debt",
    # 偿债
    "流动比率": "current_ratio",
    "速动比率": "quick_ratio",
    "现金比率(%)": "cash_ratio",
    "现金流量比率(%)": "cash_flow_ratio",
    "资产负债率(%)": "debt_to_assets",
    "负债与所有者权益比率(%)": "equity_multiplier",
    "产权比率(%)": "debt_to_equity",
    "股东权益比率(%)": "equity_ratio",
    "长期负债比率(%)": "long_debt_ratio",
    "固定资产比重(%)": "fixed_asset_ratio",
    # 营运
    "应收账款周转率(次)": "ar_turnover",
    "应收账款周转天数(天)": "ar_turnover_days",
    "存货周转天数(天)": "inventory_turnover_days",
    "存货周转率(次)": "inventory_turnover",
    "固定资产周转率(次)": "fixed_asset_turnover",
    "总资产周转率(次)": "total_asset_turnover",
    "总资产周转天数(天)": "total_asset_turnover_days",
    "流动资产周转率(次)": "current_asset_turnover",
    "流动资产周转天数(天)": "current_asset_turnover_days",
    "股东权益周转率(次)": "equity_turnover",
}


def _infer_report_type(d: date) -> str:
    m, day = d.month, d.day
    if m == 3 and day == 31:
        return "Q1"
    if m == 6 and day == 30:
        return "H1"
    if m == 9 and day == 30:
        return "Q3"
    if m == 12 and day == 31:
        return "Annual"
    return ""


class SinaMainIndicatorCollector(BaseCollector):
    name = "sina_main_indicator"
    description = "采集新浪主要财务指标(覆盖东财『主要指标』页 80+ 字段)"

    def collect_one(self, stock: StockBasic, db: Session) -> dict:
        code = stock.stock_code.split(".")[0]  # 600879.SH -> 600879
        try:
            df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2020")
        except Exception as e:
            log.warning("[%s] stock_financial_analysis_indicator 失败: %s", code, e)
            return {"ok": False, "reason": str(e)}

        if df is None or df.empty:
            return {"ok": False, "reason": "empty df"}

        inserted = 0
        updated = 0
        for _, row in df.iterrows():
            raw_date = row.get("日期")
            if pd.isna(raw_date):
                continue
            try:
                rd = pd.to_datetime(raw_date).date()
            except Exception:
                continue
            rtype = _infer_report_type(rd)
            if not rtype:
                continue

            # 找已存在记录
            obj = (
                db.query(FinMainIndicator)
                .filter(
                    FinMainIndicator.stock_code == stock.stock_code,
                    FinMainIndicator.report_date == rd,
                )
                .one_or_none()
            )
            is_new = obj is None
            if is_new:
                obj = FinMainIndicator(
                    stock_code=stock.stock_code, report_date=rd, report_type=rtype
                )

            for sina_col, model_field in _COL_MAP.items():
                if sina_col not in df.columns:
                    continue
                v = row.get(sina_col)
                if pd.isna(v):
                    continue
                try:
                    setattr(obj, model_field, Decimal(str(v)))
                except Exception:
                    pass

            if is_new:
                db.add(obj)
                inserted += 1
            else:
                updated += 1

        db.flush()
        return {"ok": True, "rows": len(df), "inserted": inserted, "updated": updated}

    def run(self, db: Session, stocks: Iterable[StockBasic] | None = None) -> dict:
        if stocks is None:
            stocks = db.query(StockBasic).all()
        total = {"ok": 0, "fail": 0, "rows": 0}
        for s in stocks:
            r = self.collect_one(s, db)
            if r.get("ok"):
                total["ok"] += 1
                total["rows"] += r.get("rows", 0)
            else:
                total["fail"] += 1
            db.commit()
        return total


if __name__ == "__main__":
    with db_session() as db:
        c = SinaMainIndicatorCollector()
        print(c.run(db))
