"""Sina 行业 + 公告 采集器（替代东方财富 EM，因 EM datacenter 在当前网络下被拒）。

数据源:
  - 行业(申万一级): http://vip.stock.finance.sina.com.cn/corp/go.php/vCI_CorpOtherInfo/stockid/{stockid}/menu_num/2.phtml
  - 公告列表:       http://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllBulletin/stockid/{stockid}.phtml
  - 公告 PDF:       公告详情页解析出 file.finance.sina.com.cn 链接

写入:
  - stock_basic.industry  (申万一级行业)
  - ann_announcement      (公告标题/类型/日期/PDF)
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
import requests

from app.db import db_session
from app.models import StockBasic, Announcement
from .base import BaseCollector


# Sina 股票代码 -> 内部 stock_code 转换
def to_sina_bare_code(stock_code: str) -> str:
    """600879.SH -> 600879"""
    return stock_code.split(".")[0]


# Sina 个股公告页 URL 模板
_LIST_URL = "http://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllBulletin/stockid/{sid}.phtml"
_INDUSTRY_URL = "http://vip.stock.finance.sina.com.cn/corp/go.php/vCI_CorpOtherInfo/stockid/{sid}/menu_num/2.phtml"

# 公告类型归一 (复用 EM collector 的归一表)
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
    "审计报告": "其他",
    "评估报告": "其他",
    "律师意见": "其他",
    "法律意见书": "其他",
    "管理办法": "公司治理",
    "薪酬": "公司治理",
    "独立董事": "公司治理",
    "换届": "公司治理",
    "回购": "股权激励",
    "股东会": "股东大会",
    "募集资金": "重大事项",
    "理财": "重大事项",
    "兑付": "重大事项",
    "融资": "重大事项",
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


def _gbk_get(url: str, timeout: int = 10) -> str:
    r = requests.get(url, timeout=timeout, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://vip.stock.finance.sina.com.cn/",
    })
    r.encoding = "gbk"
    return r.text


class SinaIndustryCollector(BaseCollector):
    """Sina 行业采集（申万一级）"""

    def __init__(self):
        super().__init__("sina_industry")

    def _fetch(self, stock_code: str) -> str | None:
        sid = to_sina_bare_code(stock_code)
        url = _INDUSTRY_URL.format(sid=sid)
        try:
            html = _gbk_get(url)
        except Exception as exc:
            self.log.warning("[%s] 行业页抓取失败: %s", stock_code, exc)
            return None
        # 行业所在行: <td class="ct" align="center">航天装备</td>
        m = re.search(r"所属行业板块[\s\S]{0,500}?<td[^>]*class=\"ct\"[^>]*align=\"center\"[^>]*>([^<]+?)</td>", html)
        if not m:
            return None
        industry = m.group(1).strip()
        if industry in ("点击查看", ""):
            return None
        return industry

    def collect_one(self, stock_code: str) -> str | None:
        return self._fetch(stock_code)

    def collect(self, stock_codes: list[str]) -> dict[str, str]:
        results: dict[str, str] = {}
        with db_session() as session:
            for sc in stock_codes:
                industry = self._fetch(sc)
                if industry:
                    results[sc] = industry
                    sb = session.query(StockBasic).filter(StockBasic.stock_code == sc).first()
                    if sb is not None:
                        sb.industry = industry
            session.commit()
        self.log.info("Sina 行业完成, 写入 %d 只", len(results))
        return results


def collect_industry(stock_codes: list[str]) -> dict[str, str]:
    return SinaIndustryCollector().collect(stock_codes)


class SinaAnnouncementCollector(BaseCollector):
    """Sina 公告采集（列表 + PDF 链接解析）"""

    def __init__(self):
        super().__init__("sina_announcement")

    def _fetch_list(self, stock_code: str, pages: int = 3) -> list[dict]:
        """抓取公告列表, 返回 [{title, date, pdf_url, ann_type_raw}]"""
        sid = to_sina_bare_code(stock_code)
        out: list[dict] = []
        for page in range(1, pages + 1):
            url = _LIST_URL.format(sid=sid)
            if page > 1:
                url += f"?Page={page}"
            try:
                html = _gbk_get(url)
            except Exception as exc:
                self.log.warning("[%s] 公告列表第 %d 页失败: %s", stock_code, page, exc)
                continue
            # 匹配 "YYYY-MM-DD&nbsp;<a target='_blank' href='/corp/view/vCB_AllBulletinDetail.php?stockid=600879&id=12398658'>航天电子：xxx</a>"
            # 用 [\s\S] 跨行匹配更稳
            pattern = re.compile(
                r"(\d{4}-\d{2}-\d{2})&nbsp;.*?href='/corp/view/vCB_AllBulletinDetail\.php\?stockid=\d+&id=(\d+)'[^>]*>([^<]+)</a>",
                re.DOTALL,
            )
            for m in pattern.finditer(html):
                pub_date, ann_id, title = m.group(1), m.group(2), m.group(3).strip()
                if not title or "下载公告" in title:
                    continue
                out.append({
                    "publish_date": pub_date,
                    "title": title,
                    "detail_url": f"http://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?stockid={sid}&id={ann_id}",
                    "detail_id": ann_id,
                })
            if not out:
                break
        return out

    def _fetch_pdf_url(self, detail_url: str) -> str | None:
        """从公告详情页提取 PDF 链接"""
        try:
            html = _gbk_get(detail_url)
        except Exception:
            return None
        m = re.search(r"href='(http://file\.finance\.sina\.com\.cn[^']+\.PDF)'", html, re.IGNORECASE)
        if not m:
            return None
        return m.group(1)

    def collect(self, stock_code: str, pages: int = 3, fetch_pdf: bool = False) -> list[dict]:
        """采集单只股票的公告, 写入数据库.

        :param fetch_pdf: 是否解析详情页获取 PDF URL (慢, 默认 False, 用 detail_url 兜底)
        """
        items = self._fetch_list(stock_code, pages=pages)
        written = 0
        with db_session() as session:
            for item in items:
                pdf_url = None
                if fetch_pdf:
                    pdf_url = self._fetch_pdf_url(item["detail_url"])
                if not pdf_url:
                    # 用 detail URL 兜底, 用户可点击进入详情页
                    pdf_url = item["detail_url"]
                pub_date = date.fromisoformat(item["publish_date"])
                title = item["title"]
                # 提取股票简称: "航天电子：xxx" -> 类型判断
                # 简单规则: 冒号后文字第一个段做类型
                ann_type_raw = ""
                if "：" in title:
                    parts = title.split("：", 1)
                    if parts[0] == "航天电子" or parts[0] == "信维通信" or parts[0] == "西部材料" or len(parts[0]) <= 6:
                        ann_type_raw = parts[1]
                    else:
                        ann_type_raw = title
                else:
                    ann_type_raw = title
                ann_type = _normalize_type(ann_type_raw[:30])  # 取前30字做归一

                # 用 detail_id 作为去重键 (uk_stock_pdf)
                unique_key = f"sina:{item['detail_id']}"
                existing = session.query(Announcement).filter(
                    Announcement.stock_code == stock_code,
                    Announcement.pdf_url == unique_key,
                ).first()
                if existing is not None:
                    # 已存在 -> 更新
                    existing.ann_title = title
                    existing.ann_type = ann_type
                    existing.publish_date = pub_date
                    if fetch_pdf and pdf_url and pdf_url != unique_key:
                        existing.pdf_url = pdf_url
                    continue
                # 新建
                rec = Announcement(
                    stock_code=stock_code,
                    ann_title=title,
                    ann_type=ann_type,
                    publish_date=pub_date,
                    pdf_url=unique_key,  # 用 sina:detail_id 作主键
                    source="新浪",
                    is_risk=False,
                )
                # 真实 PDF URL 暂存到 pdf_url 字段, 后续 fetch_pdf 时再覆盖
                # 但 pdf_url 已被 unique_key 占用, 改存 content_summary
                rec.content_summary = pdf_url  # 暂存真实 PDF / detail URL
                session.add(rec)
                written += 1
            session.commit()
        self.log.info("[%s] 公告采集完成, 新增 %d 条, 总解析 %d 条", stock_code, written, len(items))
        return items


def collect_announcements(stock_code: str, pages: int = 3) -> list[dict]:
    return SinaAnnouncementCollector().collect(stock_code, pages=pages)
