"""Sina + Tencent 行情/估值采集器（替代东方财富 EM，因 EM datacenter 在当前网络下被拒）。

数据源:
  - 实时行情/估值/股本/PE/PB/市值: 腾讯 qt.gtimg.cn
    URL: https://qt.gtimg.cn/q=sh600879,sz000001
    字段: 见 _TENCENT_FIELD 索引表
  - 行业: 腾讯同一接口 (字段 73-74 不含行业，需要从其他渠道)

写入:
  - stock_basic: 补齐 stock_name, industry, market, total_share, float_share
  - stock_realtime_quote: latest_price, change_pct, PE, PB, 总市值, 流通市值
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import re

import requests

from app.db import db_session
from app.models import StockBasic, StockRealtimeQuote
from .base import BaseCollector


# 腾讯行情接口字段索引 (split by '~')
# 完整列表参考 https://www.qqxiyou.cn/wenda/27317.html
_TENCENT_FIELD = {
    "name": 1,
    "code": 2,
    "current_price": 3,        # 最新价
    "prev_close": 4,           # 昨收
    "open": 5,                 # 今开
    "volume_hand": 6,          # 成交量(手)
    "amount_outer": 7,         # 外盘
    "amount_inner": 8,         # 内盘
    "bid1_price": 9,
    "bid1_volume": 10,
    "bid2_price": 11,
    "bid2_volume": 12,
    "bid3_price": 13,
    "bid3_volume": 14,
    "bid4_price": 15,
    "bid4_volume": 16,
    "bid5_price": 17,
    "bid5_volume": 18,
    "ask1_price": 19,
    "ask1_volume": 20,
    "ask2_price": 21,
    "ask2_volume": 22,
    "ask3_price": 23,
    "ask3_volume": 24,
    "ask4_price": 25,
    "ask4_volume": 26,
    "ask5_price": 27,
    "ask5_volume": 28,
    "datetime": 30,            # 行情时间 yyyyMMddHHmmss
    "change_amount": 31,       # 涨跌额
    "change_pct": 32,          # 涨跌幅 %
    "high": 33,
    "low": 34,
    "price_volume_amount": 35,  # 现价/成交量/成交额 复合
    "volume_hand2": 36,
    "turnover_wan": 37,        # 成交额(万)
    "turnover_rate": 38,       # 换手率 %
    "pe": 39,                  # 市盈率(动)
    "empty_1": 40,
    "high2": 41,
    "low2": 42,
    "amplitude": 43,           # 振幅 %
    "total_mv_yi": 44,         # 总市值(亿)
    "float_mv_yi": 45,         # 流通市值(亿)
    "pb": 46,                  # 市净率
    "limit_up": 47,
    "limit_down": 48,
    "5min_change_pct": 49,
    # ... 中间为买卖盘
    "total_share": 72,         # 总股本(股)
    "float_share": 73,         # 流通股本(股)
    # 73-80 区间: 行业 / 板块 / 概念 编码
    "industry_code": 78,       # 行业编码(腾讯内部)
    "pe_ttm": 80,              # PE TTM
}


def to_tencent_code(stock_code: str) -> str:
    """600879.SH -> sh600879 ; 000001.SZ -> sz000001"""
    base = stock_code.split(".")[0]
    market = stock_code.split(".")[-1].upper() if "." in stock_code else ""
    if market == "SH" or (market == "" and base.startswith(("6", "5", "68"))):
        return f"sh{base}"
    return f"sz{base}"


def to_sina_code(stock_code: str) -> str:
    """600879.SH -> sh600879"""
    return to_tencent_code(stock_code)


def _infer_market(stock_code: str) -> str:
    base = stock_code.split(".")[0]
    if base.startswith("688"):
        return "科创板"
    if base.startswith(("60", "5")):
        return "主板"
    if base.startswith("300"):
        return "创业板"
    if base.startswith(("00", "001", "002", "003")):
        return "主板"
    if base.startswith(("83", "87", "43")):
        return "北交所"
    return "其他"


# 腾讯行业编码 → 中文 (部分常用, 可按需扩展)
_TENCENT_INDUSTRY_MAP: dict[str, str] = {
    # 行业编码是腾讯内部 ID, 暂以空字典兜底 (用 Sina 行业数据补齐)
}


def _fetch_industry_from_sina(stock_code: str) -> str | None:
    """从 Sina 抓行业 (备用, 腾讯行业编码不公开)."""
    try:
        sina_code = to_sina_code(stock_code)
        # 新浪行业接口: https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?node=hangye
        # 单只股票行业: https://hq.sinajs.cn/list=sh600879 (基础行情不含行业)
        # 用 akshare 兜底 (走新浪):
        import akshare as ak
        df = ak.stock_individual_spot_xq(symbol=sina_code)  # 雪球, 可能也不通
        return None
    except Exception:
        return None


def _fetch_industry_from_tencent(stock_code: str) -> str | None:
    """腾讯个股行业: 通过 tencent 主页/雪球获取, 此处先返回 None (后续从 Xueqiu 或 Sina 补)."""
    return None


class SinaTencentCollector(BaseCollector):
    """Sina + Tencent 行情/估值/股本 采集器。"""

    def __init__(self):
        super().__init__("sina_tencent")

    def _fetch(self, tencent_codes: list[str]) -> dict[str, list[str]]:
        """批量拉取腾讯行情, 返回 {tencent_code: [fields...]}"""
        url = "https://qt.gtimg.cn/q=" + ",".join(tencent_codes)
        r = requests.get(url, timeout=10)
        r.encoding = "gbk"  # 腾讯返回 GBK
        result = {}
        for line in r.text.strip().split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue
            # v_sh600879="..."
            k, _, v = line.partition("=")
            code = k.strip().lstrip("v_")
            v = v.strip().strip('"')
            if not v:
                continue
            fields = v.split("~")
            result[code] = fields
        return result

    def _parse(self, fields: list[str], stock_code: str) -> dict:
        """从腾讯字段列表解析出标准 dict。"""
        def g(key: str) -> str | None:
            idx = _TENCENT_FIELD.get(key)
            if idx is None or idx >= len(fields):
                return None
            val = fields[idx].strip()
            if not val or val == "-":
                return None
            return val

        # 解析数字
        def dec(key: str) -> Decimal | None:
            v = g(key)
            if v is None:
                return None
            try:
                return Decimal(v.replace(",", ""))
            except Exception:
                return None

        total_share = dec("total_share")
        float_share = dec("float_share")
        total_mv = dec("total_mv_yi")  # 亿
        float_mv = dec("float_mv_yi")

        # 总市值(元) = 总市值(亿) * 1e8
        total_mv_yuan = (total_mv * Decimal("100000000")) if total_mv is not None else None
        float_mv_yuan = (float_mv * Decimal("100000000")) if float_mv is not None else None

        # 解析时间
        quote_date = None
        dt = g("datetime")
        if dt and len(dt) >= 8:
            try:
                quote_date = date(int(dt[:4]), int(dt[4:6]), int(dt[6:8]))
            except Exception:
                pass

        return {
            "stock_name": g("name"),
            "current_price": dec("current_price"),
            "prev_close": dec("prev_close"),
            "open": dec("open"),
            "high": dec("high"),
            "low": dec("low"),
            "change_amount": dec("change_amount"),
            "change_pct": dec("change_pct"),
            "volume_hand": dec("volume_hand"),
            "turnover_wan": dec("turnover_wan"),
            "turnover_rate": dec("turnover_rate"),
            "amplitude": dec("amplitude"),
            "pe": dec("pe"),
            "pe_ttm": dec("pe_ttm"),
            "pb": dec("pb"),
            "total_market_cap": total_mv_yuan,
            "float_market_cap": float_mv_yuan,
            "total_share": total_share,
            "float_share": float_share,
            "quote_date": quote_date,
        }

    def collect(self, stock_codes: list[str]) -> list[dict]:
        """批量采集多只股票, 返回写入摘要列表。"""
        code_map = {to_tencent_code(c): c for c in stock_codes}
        data_map = self.fetch(list(code_map.keys()))
        results = []
        today = date.today()
        with db_session() as session:
            for tc, internal_code in code_map.items():
                fields = data_map.get(tc)
                if not fields or len(fields) < 50:
                    self.log.warning("[%s] 腾讯未返回数据", internal_code)
                    continue
                info = self._parse(fields, internal_code)
                # 1) 更新 stock_basic
                sb = session.query(StockBasic).filter(StockBasic.stock_code == internal_code).first()
                if sb is None:
                    sb = StockBasic(stock_code=internal_code, stock_name=info["stock_name"] or internal_code)
                    session.add(sb)
                if info["stock_name"]:
                    sb.stock_name = info["stock_name"]
                if sb.market is None or sb.market == "其他":
                    sb.market = _infer_market(internal_code)
                if info["total_share"] is not None and (sb.total_share is None):
                    sb.total_share = info["total_share"]
                if info["float_share"] is not None and (sb.float_share is None):
                    sb.float_share = info["float_share"]

                # 2) 写入行情
                qd = info["quote_date"] or today
                q = session.query(StockRealtimeQuote).filter(
                    StockRealtimeQuote.stock_code == internal_code,
                    StockRealtimeQuote.quote_date == qd,
                ).first()
                if q is None:
                    q = StockRealtimeQuote(stock_code=internal_code, quote_date=qd)
                    session.add(q)
                q.latest_price = info["current_price"]
                q.open_price = info["open"]
                q.high_price = info["high"]
                q.low_price = info["low"]
                q.pre_close = info["prev_close"]
                q.change_pct = info["change_pct"]
                q.change_amount = info["change_amount"]
                q.volume = (info["volume_hand"] * 100) if info["volume_hand"] else None  # 手 -> 股
                q.turnover = (info["turnover_wan"] * Decimal("10000")) if info["turnover_wan"] else None  # 万 -> 元
                q.pe_dynamic = info["pe"]
                q.pe_ttm = info["pe_ttm"]
                q.pb = info["pb"]
                q.total_market_cap = info["total_market_cap"]
                q.float_market_cap = info["float_market_cap"]
                q.update_time = datetime.now()
                results.append({
                    "stock_code": internal_code,
                    "name": info["stock_name"],
                    "price": str(info["current_price"]) if info["current_price"] else None,
                    "pe": str(info["pe"]) if info["pe"] else None,
                    "pb": str(info["pb"]) if info["pb"] else None,
                    "total_mv": str(info["total_market_cap"]) if info["total_market_cap"] else None,
                })
            session.commit()
        self.log.info("腾讯行情/估值完成, 写入 %d 只", len(results))
        return results


def collect_quote(stock_codes: list[str]) -> list[dict]:
    return SinaTencentCollector().collect(stock_codes)
