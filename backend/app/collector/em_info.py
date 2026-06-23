"""东方财富个股基本信息采集器。

数据源: akshare.stock_individual_info_em
覆盖字段:
  - 股票代码 / 名称 / 简称
  - 行业 (申万一级) / 总股本 / 流通股本
  - 上市时间 / 公司全称
  - 实时 PE / PB / 总市值

写入 stock_basic 表 (按 stock_code upsert)。
"""
from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime

import pandas as pd
import akshare as ak

from app.db import db_session
from app.models import StockBasic, StockRealtimeQuote
from .base import BaseCollector


# 行业归一: 东方财富"申万行业"会带 申万一级 / 申万二级 前缀，这里统一为一级
_INDUSTRY_PREFIX = "申万"


def _normalize_industry(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    if s.startswith(_INDUSTRY_PREFIX):
        # "申万一级行业-电子" -> "电子" ; "申万二级行业-半导体" -> "半导体"
        s = s.split("-", 1)[-1].strip()
    return s or None


def _infer_market(stock_code: str) -> str:
    """由股票代码推断市场。"""
    base = stock_code.split(".")[0]
    if base.startswith(("60", "68")):
        if base.startswith("688"):
            return "科创板"
        return "主板"
    if base.startswith(("30", "00")):
        if base.startswith("300"):
            return "创业板"
        return "主板"
    if base.startswith(("83", "87", "43")):
        return "北交所"
    return "其他"


def to_em_code(stock_code: str) -> str:
    """600519.SH -> 1.600519 ; 000001.SZ -> 0.000001"""
    base = stock_code.split(".")[0]
    market = stock_code.split(".")[-1].upper() if "." in stock_code else ""
    if market == "SH" or (market == "" and base.startswith(("6", "5", "68"))):
        return f"1.{base}"
    return f"0.{base}"


class EMInfoCollector(BaseCollector):
    """东方财富个股基本信息采集器。"""

    def __init__(self):
        super().__init__("em_info")

    def _fetch(self, em_code: str) -> pd.DataFrame:
        df = ak.stock_individual_info_em(symbol=em_code)
        if df is None or len(df) == 0:
            raise RuntimeError(f"stock_individual_info_em 返回空: {em_code}")
        return df

    def _df_to_dict(self, df: pd.DataFrame) -> dict:
        """将 item/value 两列 DataFrame 转成 dict。"""
        out: dict = {}
        for _, row in df.iterrows():
            k = str(row.get("item", "")).strip()
            v = row.get("value")
            if k and v is not None and str(v).strip() and str(v).strip() != "None":
                out[k] = v
        return out

    def collect(self, stock_code: str) -> dict:
        em_code = to_em_code(stock_code)
        df = self.fetch(em_code)
        info = self._df_to_dict(df)

        # 取关键字段
        industry = _normalize_industry(info.get("行业"))
        total_share = self.to_decimal(info.get("总股本"))
        float_share = self.to_decimal(info.get("流通股本"))
        list_date = self.to_date(info.get("上市时间"))
        full_name = info.get("公司全称") or info.get("公司名称")
        latest_price = self.to_decimal(info.get("最新"))
        change_pct = self.to_decimal(info.get("涨跌幅"))
        change_amount = self.to_decimal(info.get("涨跌额"))
        pe_dynamic = self.to_decimal(info.get("市盈率(动)"))
        pb = self.to_decimal(info.get("市净率"))
        total_market_cap = self.to_decimal(info.get("总市值"))
        float_market_cap = self.to_decimal(info.get("流通市值"))
        # 涨跌幅如果是百分数(EM 直接以小数返回)，保持原值
        market = _infer_market(stock_code)

        with db_session() as session:
            basic = session.query(StockBasic).filter(StockBasic.stock_code == stock_code).first()
            if basic is None:
                basic = StockBasic(stock_code=stock_code)
                session.add(basic)

            basic.stock_name = info.get("股票简称", basic.stock_name or stock_code)
            if full_name:
                basic.full_name = str(full_name)
            basic.industry = industry or basic.industry
            basic.market = market
            if list_date:
                basic.list_date = list_date
            if total_share is not None:
                basic.total_share = total_share
            if float_share is not None:
                basic.float_share = float_share
            basic.em_code = em_code
            basic.update_time = datetime.now()
            session.commit()

            # 同步写入当日行情快照
            quote_date = date.today()
            quote = (
                session.query(StockRealtimeQuote)
                .filter(StockRealtimeQuote.stock_code == stock_code,
                        StockRealtimeQuote.quote_date == quote_date)
                .first()
            )
            if quote is None:
                quote = StockRealtimeQuote(stock_code=stock_code, quote_date=quote_date)
                session.add(quote)
            quote.latest_price = latest_price
            quote.change_pct = change_pct
            quote.change_amount = change_amount
            quote.pe_dynamic = pe_dynamic
            quote.pb = pb
            quote.total_market_cap = total_market_cap
            quote.float_market_cap = float_market_cap
            quote.update_time = datetime.now()
            session.commit()

        self.log.info("[%s] EM info 写入完成 industry=%s total_share=%s", stock_code, industry, total_share)
        return {
            "stock_code": stock_code,
            "em_code": em_code,
            "industry": industry,
            "total_share": str(total_share) if total_share is not None else None,
            "float_share": str(float_share) if float_share is not None else None,
            "latest_price": str(latest_price) if latest_price is not None else None,
            "pe_dynamic": str(pe_dynamic) if pe_dynamic is not None else None,
            "pb": str(pb) if pb is not None else None,
        }


def collect_em_info(stock_code: str) -> dict:
    return EMInfoCollector().collect(stock_code)
