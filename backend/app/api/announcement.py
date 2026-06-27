"""公告信息 API - 从东方财富实时获取公告数据"""
import logging
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd

from app.db import get_db
from app.core.response import success_response

router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])


@router.get("/")
def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    ann_type: Optional[str] = None,
    stock: Optional[str] = None,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """获取公告列表，从东方财富实时获取数据，支持按股票代码/名称和公告类型筛选"""
    try:
        today = datetime.now().strftime("%Y%m%d")

        # 循环获取多天数据
        all_data = []
        for i in range(min(days, 30)):  # 最多30天
            date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            try:
                df = ak.stock_notice_report(symbol="全部", date=date)
                if df is not None and len(df) > 0:
                    all_data.append(df)
            except Exception as e:
                logging.warning(f"获取 {date} 公告失败: {e}")
                continue

        if not all_data:
            return success_response({
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            })

        # 合并所有数据
        df = pd.concat(all_data, ignore_index=True)
        # 去重
        df = df.drop_duplicates(subset=['代码', '公告标题', '公告日期'], keep='first')

        if df is None or len(df) == 0:
            return success_response({
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            })

        # 过滤
        if stock:
            stock_clean = stock.strip().upper()
            if stock_clean.isdigit():
                # 按代码过滤
                df = df[df['代码'].astype(str).str.contains(stock_clean, na=False)]
            else:
                # 按名称过滤
                df = df[df['名称'].astype(str).str.contains(stock_clean, na=False)]

        if ann_type:
            df = df[df['公告类型'].astype(str) == ann_type]

        if keyword:
            df = df[df['公告标题'].astype(str).str.contains(keyword, na=False)]

        # 按日期倒序
        df = df.sort_values('公告日期', ascending=False)

        total = len(df)
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        page_df = df.iloc[start:end]

        result = []
        for _, row in page_df.iterrows():
            ann_date = row.get('公告日期', '')
            if isinstance(ann_date, str) and len(ann_date) >= 10:
                ann_date_str = ann_date[:10]
            else:
                ann_date_str = str(ann_date)[:10] if ann_date else ''

            result.append({
                "stock_code": str(row.get('代码', '')),
                "stock_name": str(row.get('名称', '')),
                "title": str(row.get('公告标题', '')),
                "ann_type": str(row.get('公告类型', '')),
                "disclosure_date": ann_date_str,
                "url": str(row.get('网址', '')),
            })

        return success_response({
            "items": result,
            "total": total,
            "page": page,
            "page_size": page_size,
        })
    except Exception as e:
        logging.error(f"获取公告列表失败: {e}")
        return success_response({
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "error": str(e),
        })


@router.get("/types")
def get_announcement_types():
    """获取公告类型列表"""
    return success_response([
        "全部",
        "定期报告",
        "业绩预告",
        "重大事项",
        "风险提示",
        "分配方案实施",
        "股份质押、冻结",
        "回购预案",
        "高管人员任职变动",
        "法律意见书",
        "监事会决议公告",
        "股东会决议公告",
    ])
