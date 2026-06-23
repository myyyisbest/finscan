"""采集适配器基类 —— 提供重试/随机延时/熔断/日志。

所有数据采集适配器继承 BaseCollector，调用 self._fetch() 实现实际抓取逻辑。

注意: AkShare 内部用 requests.Session 默认 User-Agent 经常被东财/Wind 服务器拒绝。
本模块在 import 时替换默认 session 的 headers (全局生效)。
"""
import random
import time
from datetime import datetime
from typing import Any

import requests

from app.core.config import settings
from app.core.logger import get_logger


# 全局 requests session 注入 EM 友好的 headers
def _install_em_headers():
    """为所有 requests 调用注入浏览器风格的 headers, 避免被 EM/Wind 反爬拒绝。"""
    try:
        from requests import Session
        original_init = Session.__init__

        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://quote.eastmoney.com/",
                "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            })

        Session.__init__ = patched_init
    except Exception:  # noqa: BLE001
        pass


_install_em_headers()


class FetchError(Exception):
    """抓取失败异常，可携带错误消息。"""
    pass


class BaseCollector:
    """采集器基类。

    用法:
        class MyCollector(BaseCollector):
            def _fetch(self, *args, **kwargs):
                ...  # 返回 DataFrame 或其他数据结构
    """

    def __init__(self, name: str = "base"):
        self.name = name
        self.log = get_logger(f"collector.{name}")
        self.sleep_min = float(settings.COLLECT_SLEEP_MIN)
        self.sleep_max = float(settings.COLLECT_SLEEP_MAX)
        self.retry = int(settings.COLLECT_RETRY)

    def sleep_random(self):
        """在请求之间加入随机延时，避开固定间隔被识别。"""
        delay = random.uniform(self.sleep_min, self.sleep_max)
        time.sleep(delay)

    def fetch(self, *args, **kwargs) -> Any:
        """带重试的抓取入口。"""
        last_err: Exception | None = None
        for attempt in range(1, self.retry + 1):
            try:
                self.sleep_random()
                result = self._fetch(*args, **kwargs)
                return result
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                backoff = attempt * 2.0
                self.log.warning("第%d次抓取失败: %s, backoff=%.1fs", attempt, exc, backoff)
                time.sleep(backoff)
        raise FetchError(f"{self.name} 连续{self.retry}次失败: {last_err}")

    def _fetch(self, *args, **kwargs) -> Any:
        """实际抓取逻辑。子类必须实现。"""
        raise NotImplementedError

    # ---- 工具方法 ----

    @staticmethod
    def to_date(val) -> Any:
        """将 '20231231' / '2023-12-31' / date / datetime 转为 date 对象。"""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.date()
        import datetime as _dt
        if isinstance(val, _dt.date):
            return val
        s = str(val).strip()
        if not s or s in ("nan", "--"):
            return None
        try:
            if s.isdigit() and len(s) == 8:
                return _dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            return _dt.date.fromisoformat(s[:10])
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def to_decimal(val):
        """将数值字段转为 Decimal。清洗: None/空→None；字符串带 % 的自动保留数值部分。"""
        from decimal import Decimal, InvalidOperation
        import math
        if val is None:
            return None
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return None
            return Decimal(str(val))
        s = str(val).strip()
        if not s or s in ("nan", "--", "-"):
            return None
        # 去除尾部 %；本系统所有 % 字段(毛利率、ROE、费用率)存的是百分比数值本身
        if s.endswith("%"):
            s = s[:-1].strip()
        s = s.replace(",", "")
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def report_type_for(date_val) -> str:
        """根据报告日推导 report_type (Q1/H1/Q3/Annual)。"""
        if not date_val:
            return ""
        m = date_val.month
        if m in (3,): return "Q1"
        if m == 6: return "H1"
        if m == 9: return "Q3"
        if m == 12: return "Annual"
        return ""

    @staticmethod
    def get_col(df, *candidates):
        """从 DataFrame 中获取候选列名，返回第一个存在的列。"""
        if df is None or len(df) == 0:
            return None
        for c in candidates:
                if c in df.columns:
                    return c
        return None
