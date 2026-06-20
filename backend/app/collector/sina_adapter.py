"""新浪三表采集适配器。

数据源: akshare.stock_financial_report_sina
覆盖:
  - 资产负债表 (fin_balance_sheet)
  - 利润表 (fin_income_statement)
  - 现金流量表 (fin_cash_flow)

字段映射参考 backend/field_mapping.md 第二章。
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd
import akshare as ak
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import db_session
from app.models import (
    BalanceSheet, IncomeStatement, CashFlow, CollectTaskLog, StockBasic
)
from .base import BaseCollector


# ====== 字段映射表 ======
# 优先取目标中文名（100% 覆盖的字段），若缺失则向后回退。

_BALANCE_MAP = {
    "total_assets": "资产总计",
    "total_current_assets": ["流动资产合计", "流动资产"],
    "monetary_funds": "货币资金",
    "accounts_receivable": ["应收票据及应收账款", "应收账款"],
    "inventory": "存货",
    "total_noncurrent_assets": ["非流动资产合计", "非流动资产"],
    "fixed_assets": "固定资产净值",
    "construction_in_progress": "在建工程",
    "intangible_assets": "无形资产",
    "goodwill": "商誉",
    "long_deferred_expenses": "长期待摊费用",
    "total_liabilities": ["负债合计", "负债和所有者权益(或股东权益)合计"],
    "total_current_liabilities": ["流动负债合计", "流动负债"],
    "short_term_borrowings": "短期借款",
    "accounts_payable": ["应付票据及应付账款", "应付账款"],
    "total_noncurrent_liabilities": ["非流动负债合计", "非流动负债"],
    "long_term_borrowings": "长期借款",
    "bonds_payable": "应付债券",
    "total_equity": ["所有者权益(或股东权益)合计", "所有者权益合计"],
    "share_capital": "实收资本(或股本)",
    "capital_reserve": "资本公积",
    "retained_profits": "未分配利润",
    "other_receivables": ["其他应收款(合计)", "其他应收款"],
}

_INCOME_MAP = {
    "total_revenue": "营业总收入",
    "operating_cost": "营业成本",
    "selling_expenses": "销售费用",
    "admin_expenses": "管理费用",
    "rd_expenses": "研发费用",
    "financial_expenses": "财务费用",
    "operating_profit": "营业利润",
    "total_profit": "利润总额",
    "net_profit": "净利润",
    "net_profit_parent": "归属于母公司所有者的净利润",
    "net_profit_deduct": ["扣非净利润", "扣除非经常性损益后的净利润"],
    "asset_impairment_loss": "资产减值损失",
    "other_income": "其他收益",
    "investment_income": "投资收益",
}

_CASHFLOW_MAP = {
    "operating_cash_inflow": "经营活动产生的现金流量",
    "operating_cash_net": "经营活动产生的现金流量净额",
    "sales_cash_received": "销售商品、提供劳务收到的现金",
    "investing_cash_net": "投资活动产生的现金流量净额",
    "financing_cash_net": "筹资活动产生的现金流量净额",
    "capital_expenditure": "购建固定资产、无形资产和其他长期资产所支付的现金",
    "cash_ending_balance": "期末现金及现金等价物余额",
}


class SinaFinancialCollector(BaseCollector):
    """新浪三表采集器。"""

    def __init__(self):
        super().__init__("sina")

    # ---- 公共抓取 ----
    def _fetch(self, stock_sina_code: str, symbol: str) -> pd.DataFrame:
        """获取原始 DataFrame 。失败时抛出。"""
        df = ak.stock_financial_report_sina(stock=stock_sina_code, symbol=symbol)
        if df is None or len(df) == 0:
            raise RuntimeError(f"{symbol} 返回空数据: {stock_sina_code}")
        # 统一报告日格式: "20231231" -> date
        if "报告日" in df.columns:
            df["报告日"] = pd.to_datetime(df["报告日"], format="%Y%m%d", errors="coerce").dt.date
        return df

    # ---- 业务方法 ----
    def collect_balance_sheet(self, stock_code: str, stock_sina_code: str):
        df = self.fetch(stock_sina_code, "资产负债表")
        self._upsert_fin_rows(stock_code, df, _BALANCE_MAP, BalanceSheet)
        self.log.info("[%s] 资产负债表写入 %d 行", stock_code, len(df))

    def collect_income(self, stock_code: str, stock_sina_code: str):
        df = self.fetch(stock_sina_code, "利润表")
        # 派生字段: gross_profit / gross_margin
        extra_map = dict(_INCOME_MAP)
        rows_map = self._rows_map(df, extra_map)
        for row, vals in rows_map:
            total_rev = vals.get("total_revenue")
            op_cost = vals.get("operating_cost")
            if total_rev is not None and op_cost is not None:
                vals["gross_profit"] = total_rev - op_cost
                if total_rev != 0:
                    from decimal import Decimal
                    vals["gross_margin"] = (total_rev - op_cost) * Decimal("100") / total_rev
        self._upsert_rows(stock_code, rows_map, IncomeStatement)
        self.log.info("[%s] 利润表写入 %d 行", stock_code, len(df))

    def collect_cashflow(self, stock_code: str, stock_sina_code: str):
        df = self.fetch(stock_sina_code, "现金流量表")
        extra_map = dict(_CASHFLOW_MAP)
        rows_map = self._rows_map(df, extra_map)
        for row, vals in rows_map:
            inflow = vals.get("operating_cash_inflow")
            net = vals.get("operating_cash_net")
            if inflow is not None and net is not None:
                vals["operating_cash_outflow"] = inflow - net
            capex = vals.get("capital_expenditure")
            if capex is not None and net is not None:
                vals["free_cash_flow"] = net - capex
        self._upsert_rows(stock_code, rows_map, CashFlow)
        self.log.info("[%s] 现金流量表写入 %d 行", stock_code, len(df))

    # ---- 内部工具 ----
    def _rows_map(self, df: pd.DataFrame, field_map: dict):
        """遍历 DataFrame，将每一行转成 (report_date, field_values) 对。"""
        rows = []
        for _, row in df.iterrows():
            vals = {}
            for field, cands in field_map.items():
                if isinstance(cands, str):
                    cands = [cands]
                for c in cands:
                    if c in df.columns:
                        v = self.to_decimal(row[c])
                        if v is not None:
                            vals[field] = v
                            break
            rows.append((row, vals))
        return rows

    def _upsert_fin_rows(self, stock_code: str, df: pd.DataFrame, field_map: dict, model_cls):
        rows_map = self._rows_map(df, field_map)
        self._upsert_rows(stock_code, rows_map, model_cls)

    def _upsert_rows(self, stock_code: str, rows_map: Iterable, model_cls):
        """批量 upsert 到数据库（按 stock_code + report_date 唯一键判定。"""
        with db_session() as session:
            for row, vals in rows_map:
                report_date = self.to_date(row["报告日"])
                if not report_date:
                    continue
                report_type = self.report_type_for(report_date)
                obj = (
                    session.query(model_cls)
                    .filter(
                        model_cls.stock_code == stock_code,
                        model_cls.report_date == report_date,
                    )
                    .first()
                )
                if obj is None:
                    obj = model_cls(
                        stock_code=stock_code, report_date=report_date, report_type=report_type
                    )
                    session.add(obj)
                else:
                    obj.report_type = report_type
                for field, value in vals.items():
                    if value is not None:
                        setattr(obj, field, value)
            session.commit()


# ---- 顶层工具函数 ----

def to_sina_code(stock_code: str) -> str:
    """600519.SH -> sh600519, 000001.SZ -> sz000001"""
    base = stock_code.split(".")[0]
    has_market = "." in stock_code
    market = stock_code.split(".")[-1].upper() if has_market else ""
    # 以 6/5 开头的上证/科创板 → sh；否则默认 sz
    if market == "SH" or (market == "" and base.startswith(("6", "5", "68"))):
        return f"sh{base}"
    return f"sz{base}"


def collect_one_stock(stock_code: str, stock_name: str = "") -> dict:
    """单只股票全套三大报表采集。"""
    sina_code = to_sina_code(stock_code)
    collector = SinaFinancialCollector()
    stats = {"stock_code": stock_code, "stock_name": stock_name, "sina_code": sina_code}

    # 1) 先写入股票基础信息
    with db_session() as session:
        basic = session.query(StockBasic).filter(StockBasic.stock_code == stock_code).first()
        if basic is None:
            basic = StockBasic(stock_code=stock_code, stock_name=stock_name or stock_code)
            session.add(basic)
        basic.sina_code = sina_code
        session.commit()

    for task_type, method in (
        ("balance", collector.collect_balance_sheet),
        ("income", collector.collect_income),
        ("cashflow", collector.collect_cashflow),
    ):
        try:
            method(stock_code, sina_code)
            _record_task_log(stock_code, task_type, status="done", error=None)
            stats[task_type] = "ok"
        except Exception as exc:  # noqa: BLE001
            _record_task_log(stock_code, task_type, status="failed", error=str(exc))
            stats[task_type] = f"failed: {exc}"
    return stats


def _record_task_log(stock_code: str, task_type: str, status: str, error=None) -> None:
    with db_session() as session:
        log = (
            session.query(CollectTaskLog)
            .filter(
                CollectTaskLog.stock_code == stock_code,
                CollectTaskLog.task_type == task_type,
            )
            .first()
        )
        if log is None:
            log = CollectTaskLog(stock_code=stock_code, task_type=task_type)
            session.add(log)
        log.status = status
        log.error_msg = error
        from datetime import datetime
        log.last_attempt = datetime.now()
        session.commit()
