"""东方财富公告采集器。

数据源: akshare.stock_announcement_em
用途: 拉取单只股票的公告标题/日期/PDF 链接，写入 ann_announcement 表。

EM 公告接口返回字段:
  - 公告标题
  - 公告类型 (定期报告/业绩预告/...)
  - 公告日期
  - 公告 PDF URL
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import pandas as pd
import akshare as ak

from app.db import db_session
from app.models import Announcement
from .base import BaseCollector
from .em_info import to_em_code


# 公告类型归一
_ANN_TYPE_MAP = {
    "定期报告": "定期报告",
    "年度报告": "定期报告",
    "半年度报告": "定期报告",
    "一季度报告": "定期报告",
    "三季度报告": "定期报告",
    "业绩预告": "业绩预告",
    "业绩快报": "业绩预告",
    "并购重组": "并购重组",
    "股权激励": "股权激励",
    "分红派息": "分红派息",
    "利润分配": "分红派息",
    "股东大会": "股东大会",
    "董事会决议": "公司治理",
    "监事会决议": "公司治理",
    "重大合同": "重大事项",
    "关联交易": "重大事项",
    "违规处罚": "监管问询",
    "问询函": "监管问询",
    "风险提示": "风险提示",
    "停牌": "其他",
    "复牌": "其他",
}


def _normalize_type(raw: Any) -> str:
    if not raw:
        return "其他"
    s = str(raw).strip()
    if s in _ANN_TYPE_MAP:
        return _ANN_TYPE_MAP[s]
    for k, v in _ANN_TYPE_MAP.items():
        if k in s:
            return v
    return s or "其他"


class EMAnnouncementCollector(BaseCollector):
    """东方财富公告采集。"""

    def __init__(self):
        super().__init__("em_announcement")

    def _fetch(self, em_code: str) -> pd.DataFrame:
        df = ak.stock_announcement_em(symbol=em_code)
        if df is None or len(df) == 0:
            return pd.DataFrame()
        return df

    def _detect_columns(self, df: pd.DataFrame) -> dict[str, str]:
        """根据列名识别字段对应关系。"""
        cols = [str(c) for c in df.columns]
        result = {}

        # 标题
        for c in cols:
            if "标题" in c or "公告名称" in c or "名称" in c:
                result["title"] = c
                break
        # 类型
        for c in cols:
            if "类型" in c or "公告类型" in c:
                result["type"] = c
                break
        # 日期
        for c in cols:
            if "日期" in c or "时间" in c:
                result["date"] = c
                break
        # URL
        for c in cols:
            if "URL" in c.upper() or "url" in c.lower() or "PDF" in c.upper() or "pdf" in c.lower() or "详情" in c:
                result["url"] = c
                break
        return result

    def collect(self, stock_code: str) -> int:
        em_code = to_em_code(stock_code)
        df = self.fetch(em_code)
        if df is None or len(df) == 0:
            self.log.warning("[%s] EM 公告为空", stock_code)
            return 0
        col = self._detect_columns(df)
        self.log.info("[%s] EM 公告 %d 条, 列映射=%s", stock_code, len(df), col)

        if not col.get("title") or not col.get("url"):
            self.log.warning("[%s] 列名映射失败: %s", stock_code, col)
            return 0

        with db_session() as session:
            # 已有公告 URL 集合（用于去重）
            existing_urls = {
                u[0] for u in session.query(Announcement.pdf_url)
                .filter(Announcement.stock_code == stock_code, Announcement.pdf_url != None)
                .all()
            }
            added = 0
            for _, row in df.iterrows():
                title = str(row.get(col["title"], "")).strip()
                url = str(row.get(col["url"], "")).strip()
                if not title or not url:
                    continue
                if url in existing_urls:
                    continue
                ann_type = _normalize_type(row.get(col.get("type", ""), "")) if col.get("type") else "其他"
                publish_date = self.to_date(row.get(col["date"])) if col.get("date") else None
                ann = Announcement(
                    stock_code=stock_code,
                    ann_title=title[:200],
                    ann_type=ann_type,
                    publish_date=publish_date,
                    pdf_url=url[:300],
                    source="东方财富",
                )
                session.add(ann)
                added += 1
            session.commit()
        self.log.info("[%s] 公告写入 %d 条", stock_code, added)
        return added


def collect_announcement(stock_code: str) -> int:
    return EMAnnouncementCollector().collect(stock_code)
