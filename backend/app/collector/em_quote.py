"""东方财富实时行情采集器（全 A 股）。

数据源: akshare.stock_zh_a_spot_em
用途: 拉取全市场行情快照，写入 stock_realtime_quote。
特点:
  - 数据量大(5000+)，首次跑较慢；后续按 stock_code 增量更新
  - 提供 PE / PB / 总市值 / 流通市值 / 涨跌幅
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pandas as pd
import akshare as ak

from app.db import db_session
from app.models import StockBasic, StockRealtimeQuote
from .base import BaseCollector


# EM 字段名映射（实际 EM 返回列）
_QUOTE_COL_MAP = {
    "stock_code": ["代码"],
    "stock_name": ["名称"],
    "latest_price": ["最新价"],
    "change_pct": ["涨跌幅"],
    "change_amount": ["涨跌额"],
    "volume": ["成交量"],
    "turnover": ["成交额"],
    "amplitude": ["振幅"],
    "high_price": ["最高"],
    "low_price": ["最低"],
    "open_price": ["今开"],
    "pre_close": ["昨收"],
    "pe_dynamic": ["市盈率-动态"],
    "pe_ttm": ["市盈率-TTM"],
    "pb": ["市净率"],
    "total_market_cap": ["总市值"],
    "float_market_cap": ["流通市值"],
}


def _code_to_internal(em_code: str) -> str | None:
    """1.600879 -> 600879.SH ; 0.300136 -> 300136.SZ"""
    if not em_code or "." not in str(em_code):
        return None
    market, base = str(em_code).split(".", 1)
    if not base.isdigit():
        return None
    if market == "1":
        return f"{base}.SH"
    if market == "0":
        return f"{base}.SZ"
    if market == "116":
        return f"{base}.HK"
    return None


def _get(df: pd.DataFrame, idx: int, candidates: list[str]):
    for c in candidates:
        if c in df.columns:
            return df.iloc[idx][c]
    return None


class EMQuoteCollector(BaseCollector):
    """全 A 股行情采集。"""

    def __init__(self):
        super().__init__("em_quote")

    def _fetch(self) -> pd.DataFrame:
        df = ak.stock_zh_a_spot_em()
        if df is None or len(df) == 0:
            raise RuntimeError("stock_zh_a_spot_em 返回空")
        return df

    def _build_quote_from_row(self, stock_code: str, quote_date: date, df: pd.DataFrame, idx: int) -> StockRealtimeQuote:
        """从 DataFrame 一行构造 StockRealtimeQuote。"""
        q = StockRealtimeQuote(stock_code=stock_code, quote_date=quote_date)
        q.latest_price = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["latest_price"]))
        q.open_price = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["open_price"]))
        q.high_price = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["high_price"]))
        q.low_price = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["low_price"]))
        q.pre_close = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["pre_close"]))
        q.change_pct = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["change_pct"]))
        q.change_amount = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["change_amount"]))
        q.volume = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["volume"]))
        q.turnover = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["turnover"]))
        q.pe_dynamic = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["pe_dynamic"]))
        q.pe_ttm = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["pe_ttm"]))
        q.pb = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["pb"]))
        q.total_market_cap = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["total_market_cap"]))
        q.float_market_cap = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["float_market_cap"]))
        q.update_time = datetime.now()
        return q

    def collect_all(self) -> int:
        """拉取全 A 股行情，按 (stock_code, quote_date) upsert。"""
        df = self.fetch()
        quote_date = date.today()

        # 1) 预加载已有数据
        with db_session() as session:
            basics = {s.stock_code: s for s in session.query(StockBasic).all()}
            existing_quotes = {
                q.stock_code: q
                for q in session.query(StockRealtimeQuote)
                .filter(StockRealtimeQuote.quote_date == quote_date)
                .all()
            }
            new_basics: list[StockBasic] = []
            new_quotes: list[StockRealtimeQuote] = []

            for i in range(len(df)):
                em_code = str(df.iloc[i].get("代码", "")).strip()
                stock_code = _code_to_internal(em_code)
                if not stock_code:
                    continue
                stock_name = str(df.iloc[i].get("名称", "")).strip()

                # 1. StockBasic 增量
                if stock_code in basics:
                    sb = basics[stock_code]
                    if not sb.em_code:
                        sb.em_code = em_code
                else:
                    sb = StockBasic(stock_code=stock_code, stock_name=stock_name, em_code=em_code)
                    basics[stock_code] = sb
                    new_basics.append(sb)

                # 2. Quote upsert
                if stock_code in existing_quotes:
                    q = existing_quotes[stock_code]
                    q.latest_price = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["latest_price"]))
                    q.open_price = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["open_price"]))
                    q.high_price = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["high_price"]))
                    q.low_price = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["low_price"]))
                    q.pre_close = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["pre_close"]))
                    q.change_pct = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["change_pct"]))
                    q.change_amount = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["change_amount"]))
                    q.volume = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["volume"]))
                    q.turnover = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["turnover"]))
                    q.pe_dynamic = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["pe_dynamic"]))
                    q.pe_ttm = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["pe_ttm"]))
                    q.pb = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["pb"]))
                    q.total_market_cap = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["total_market_cap"]))
                    q.float_market_cap = self.to_decimal(_get(df, i, _QUOTE_COL_MAP["float_market_cap"]))
                    q.update_time = datetime.now()
                else:
                    q = self._build_quote_from_row(stock_code, quote_date, df, i)
                    existing_quotes[stock_code] = q
                    new_quotes.append(q)

            for sb in new_basics:
                session.add(sb)
            for q in new_quotes:
                session.add(q)
            session.commit()
        self.log.info("EM quote 写入 %d (含 %d 新增 quote, %d 新增 basic)", len(df), len(new_quotes), len(new_basics))
        return len(df)

    def collect_one(self, stock_code: str) -> bool:
        """单只股票增量更新行情。"""
        quote_date = date.today()
        base = stock_code.split(".")[0]
        df = self.fetch()
        mask = df["代码"].astype(str).str.startswith(f"1.{base}", na=False) | \
               df["代码"].astype(str).str.startswith(f"0.{base}", na=False)
        if not mask.any():
            self.log.warning("[%s] EM 行情未找到", stock_code)
            return False
        idx = df[mask].index[0]
        with db_session() as session:
            quote = (
                session.query(StockRealtimeQuote)
                .filter(StockRealtimeQuote.stock_code == stock_code,
                        StockRealtimeQuote.quote_date == quote_date)
                .first()
            )
            if quote is None:
                quote = self._build_quote_from_row(stock_code, quote_date, df, idx)
                session.add(quote)
            else:
                quote.latest_price = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["latest_price"]))
                quote.open_price = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["open_price"]))
                quote.high_price = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["high_price"]))
                quote.low_price = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["low_price"]))
                quote.pre_close = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["pre_close"]))
                quote.change_pct = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["change_pct"]))
                quote.change_amount = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["change_amount"]))
                quote.volume = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["volume"]))
                quote.turnover = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["turnover"]))
                quote.pe_dynamic = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["pe_dynamic"]))
                quote.pe_ttm = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["pe_ttm"]))
                quote.pb = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["pb"]))
                quote.total_market_cap = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["total_market_cap"]))
                quote.float_market_cap = self.to_decimal(_get(df, idx, _QUOTE_COL_MAP["float_market_cap"]))
                quote.update_time = datetime.now()
            session.commit()
        return True


def collect_quote_all() -> int:
    return EMQuoteCollector().collect_all()


def collect_quote_one(stock_code: str) -> bool:
    return EMQuoteCollector().collect_one(stock_code)
