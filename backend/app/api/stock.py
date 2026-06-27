"""股票基础信息API：搜索、列表、基本信息、公司简介。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from functools import lru_cache
import logging
import pandas as pd
import time

from app.db import get_db
from app.core.response import success_response, fail_response
from app.models import StockBasic, FinReport

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])

log = logging.getLogger(__name__)

# A股股票列表缓存（代码->名称映射）
_stock_list_cache = None
_stock_list_cache_time = 0
_CACHE_TTL = 3600  # 缓存1小时


def _get_all_stocks():
    """获取所有A股列表，带缓存。"""
    global _stock_list_cache, _stock_list_cache_time
    now = time.time()
    if _stock_list_cache is not None and (now - _stock_list_cache_time) < _CACHE_TTL:
        return _stock_list_cache

    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        if df is not None and len(df) > 0:
            stocks = []
            seen = set()
            for _, row in df.iterrows():
                code = str(row.get('code', '')).zfill(6)
                name = str(row.get('name', '')).replace(' ', '').replace('\u3000', '')
                if len(code) == 6 and code.isdigit() and name and name != 'nan' and code not in seen:
                    stocks.append((code, name))
                    seen.add(code)
            _stock_list_cache = stocks
            _stock_list_cache_time = now
            log.info("加载A股列表缓存: %d 只股票", len(stocks))
            return stocks
    except Exception as e:
        log.warning("获取A股列表失败: %s", e)

    # 失败则返回空
    return []


def _detect_market(code: str) -> str:
    """根据代码判断市场"""
    code = code.strip()
    if code.startswith("6"):
        return "SH"
    elif code.startswith("0") or code.startswith("3"):
        return "SZ"
    elif code.startswith("4") or code.startswith("8"):
        return "BJ"
    return "SZ"


def _get_xq_symbol(code: str) -> str:
    """获取雪球格式的symbol（如SH601127）"""
    return f"{_detect_market(code)}{code}"


@router.get("/search")
def search_stock(
    keyword: str = Query(..., min_length=1, description="搜索关键词（代码或名称）"),
    db: Session = Depends(get_db),
):
    """搜索股票：优先从akshare全量A股列表搜索，结果自动入库。"""
    kw = keyword.strip()

    # 先查本地数据库（快速返回已有数据）
    query = db.query(StockBasic)
    if kw.isdigit():
        local_results = query.filter(StockBasic.stock_code.like(f"%{kw}%")).limit(20).all()
    else:
        local_results = query.filter(
            (StockBasic.stock_name.like(f"%{kw}%")) |
            (StockBasic.stock_code.like(f"%{kw}%"))
        ).limit(20).all()

    # 本地有结果直接返回
    if local_results:
        return success_response([{
            "stock_code": s.stock_code,
            "stock_name": s.stock_name,
            "market": s.market,
            "secucode": s.secucode or s.secucode_format(),
            "industry": s.industry,
        } for s in local_results])

    # 本地没有，从akshare全量列表搜索
    all_stocks = _get_all_stocks()
    matched = []
    kw_clean = kw.replace(' ', '').replace('\u3000', '')
    if all_stocks:
        for code, name in all_stocks:
            name_clean = name.replace(' ', '').replace('\u3000', '')
            if kw.isdigit():
                if kw in code:
                    matched.append((code, name))
            else:
                if kw_clean in name_clean or kw in code:
                    matched.append((code, name))
            if len(matched) >= 20:
                break

    if matched:
        results = []
        for code, name in matched:
            # 自动入库
            existing = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
            if not existing:
                market = _detect_market(code)
                s = StockBasic(
                    stock_code=code,
                    market=market,
                    secucode=f"{market}{code}",
                    stock_name=name,
                )
                db.add(s)
            market = _detect_market(code)
            results.append({
                "stock_code": code,
                "stock_name": name,
                "market": market,
                "secucode": f"{market}{code}",
                "industry": None,
            })
        db.commit()
        return success_response(results)

    return success_response([])


@router.get("/{code}")
def get_stock_info(code: str, db: Session = Depends(get_db)):
    """获取股票基本信息。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    stock = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
    if not stock:
        return fail_response("股票不存在", code=404)

    # 获取最新一期财务数据
    latest_report = (
        db.query(FinReport)
        .filter(FinReport.stock_code == code)
        .order_by(FinReport.report_date.desc())
        .first()
    )

    return success_response({
        "stock_code": stock.stock_code,
        "stock_name": stock.stock_name,
        "market": stock.market,
        "secucode": stock.secucode or stock.secucode_format(),
        "industry": stock.industry,
        "full_name": stock.full_name,
        "list_date": str(stock.list_date) if stock.list_date else None,
        "is_st": stock.is_st,
        "latest_report": {
            "report_date": str(latest_report.report_date) if latest_report else None,
            "report_name": latest_report.report_name if latest_report else None,
            "total_revenue": float(latest_report.total_revenue) if latest_report and latest_report.total_revenue else None,
            "net_profit_parent": float(latest_report.net_profit_parent) if latest_report and latest_report.net_profit_parent else None,
            "roe": float(latest_report.roe) if latest_report and latest_report.roe else None,
            "debt_ratio": float(latest_report.debt_ratio) if latest_report and latest_report.debt_ratio else None,
        } if latest_report else None,
    })


@router.get("/{code}/reports/dates")
def get_report_dates(
    code: str,
    report_type: Optional[str] = Query(None, description="Q1/H1/Q3/Annual"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """获取某股票的可用报告期列表（倒序）。"""
    code = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    query = db.query(FinReport).filter(FinReport.stock_code == code)
    if report_type:
        query = query.filter(FinReport.report_type == report_type)
    reports = query.order_by(FinReport.report_date.desc()).limit(limit).all()
    return success_response([{
        "report_date": str(r.report_date),
        "report_name": r.report_name,
        "report_type": r.report_type,
        "notice_date": str(r.notice_date) if r.notice_date else None,
    } for r in reports])


@router.get("/{code}/profile")
def get_stock_profile(code: str, db: Session = Depends(get_db)):
    """获取公司简介 + 最新公告：优先从数据库读取，没有则实时获取入库。

    返回字段：
    - basic: 数据库中的基础信息
    - profile: 公司概况（巨潮 cninfo）
    - announcements: 最新公告列表
    - error: 错误信息
    """
    code_clean = code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "")

    # 数据库基础信息
    stock = db.query(StockBasic).filter(StockBasic.stock_code == code_clean).first()
    basic_info = {
        "stock_code": stock.stock_code if stock else code_clean,
        "stock_name": stock.stock_name if stock else None,
        "full_name": stock.full_name if stock else None,
        "industry": stock.industry if stock else None,
        "market": stock.market if stock else _detect_market(code_clean),
        "list_date": str(stock.list_date) if stock and stock.list_date else None,
    }

    # 1) 公司简介：优先用数据库已有字段，没有则实时获取并更新
    profile_data = None
    profile_error = None

    # 如果数据库已经有 full_name 和 industry，直接构造基础profile
    if stock and stock.full_name:
        profile_data = {
            "公司名称": stock.full_name or "",
            "A股代码": stock.stock_code or "",
            "A股简称": stock.stock_name or "",
            "所属行业": stock.industry or "",
            "上市日期": str(stock.list_date) if stock.list_date else "",
        }

    # 如果数据库信息不全，尝试实时获取
    if not profile_data or not profile_data.get("公司名称"):
        try:
            import akshare as ak
            df = ak.stock_profile_cninfo(symbol=code_clean)
            if df is not None and len(df) > 0:
                row = df.iloc[0]
                profile_data = {col: str(row[col]) if row[col] is not None else '' for col in df.columns}
                # 更新数据库
                if stock:
                    full_name = str(row.get("公司名称", "")).strip()
                    industry = str(row.get("所属行业", "")).strip()
                    from datetime import datetime
                    list_date_str = str(row.get("上市日期", "")).strip()
                    if full_name and full_name != "nan":
                        stock.full_name = full_name
                    if industry and industry != "nan":
                        stock.industry = industry
                    if list_date_str and list_date_str != "nan":
                        try:
                            from app.collector.em_collector import _to_date
                            stock.list_date = _to_date(list_date_str)
                        except Exception:
                            pass
                    db.commit()
        except Exception as e:
            profile_error = str(e)
            log.warning("akshare stock_profile_cninfo 失败: %s", e)

    # 2) 公告：优先从数据库读取，没有则实时获取并入库
    from app.models import Announcement
    from datetime import datetime, timedelta
    announcements = []
    announce_error = None

    # 先查数据库
    cutoff_date = (datetime.now() - timedelta(days=180)).date()
    db_anns = (
        db.query(Announcement)
        .filter(Announcement.stock_code == code_clean, Announcement.publish_date >= cutoff_date)
        .order_by(Announcement.publish_date.desc())
        .limit(20)
        .all()
    )

    if db_anns:
        for ann in db_anns:
            announcements.append({
                "title": ann.ann_title,
                "date": str(ann.publish_date),
                "time": str(ann.publish_date),
                "sec_name": stock.stock_name if stock else "",
                "url": ann.pdf_url or "",
                "ann_type": ann.ann_type or "",
            })
    else:
        # 数据库没有，实时获取并入库
        try:
            import akshare as ak
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
            df_ann = ak.stock_individual_notice_report(
                security=code_clean,
                symbol="全部",
                begin_date=start_date,
                end_date=end_date,
            )
            if df_ann is not None and len(df_ann) > 0:
                df_ann = df_ann.sort_values("公告日期", ascending=False)
                # 入库
                for _, row in df_ann.iterrows():
                    ann_date = row.get("公告日期", "")
                    ann_date_str = ""
                    if ann_date is not None and str(ann_date) != "nan":
                        try:
                            ann_date_str = pd.Timestamp(ann_date).strftime("%Y-%m-%d")
                        except Exception:
                            ann_date_str = str(ann_date)[:10]
                    announcements.append({
                        "title": str(row.get("公告标题", "")),
                        "date": ann_date_str,
                        "time": ann_date_str,
                        "sec_name": str(row.get("名称", "")),
                        "url": str(row.get("网址", "")),
                        "ann_type": str(row.get("公告类型", "")),
                    })
                    # 去重入库
                    try:
                        from datetime import date as date_type
                        pub_date = None
                        if ann_date_str:
                            pub_date = datetime.strptime(ann_date_str, "%Y-%m-%d").date()
                        if pub_date:
                                existing = db.query(Announcement).filter(
                                    Announcement.stock_code == code_clean,
                                    Announcement.ann_title == str(row.get("公告标题", "")),
                                    Announcement.publish_date == pub_date,
                                ).first()
                                if not existing:
                                    ann_obj = Announcement(
                                        stock_code=code_clean,
                                        ann_title=str(row.get("公告标题", "")),
                                        ann_type=str(row.get("公告类型", "")) or None,
                                        publish_date=pub_date,
                                        pdf_url=str(row.get("网址", "")) or None,
                                        source="eastmoney",
                                    )
                                    db.add(ann_obj)
                    except Exception:
                        pass
                db.commit()
        except Exception as e:
            announce_error = str(e)
            log.warning("akshare stock_individual_notice_report 失败: %s", e)

    return success_response({
        "basic": basic_info,
        "profile": profile_data,
        "profile_error": profile_error,
        "announcements": announcements[:20],  # 只返回前20条
        "announce_error": announce_error,
    })
