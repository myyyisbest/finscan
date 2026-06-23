"""SQLAlchemy ORM 模型 —— 东方财富 F10 风格设计。

核心设计：
- 三表（资产负债表/利润表/现金流量表）数据用 JSON 存储原始响应，
  同时提取关键指标列用于列表页快速查询排序。
- 所有金额单位：元（东方财富接口原始单位）。
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Integer, String, Text, DECIMAL, Date, DateTime, Boolean,
    ForeignKey, Index, UniqueConstraint, SmallInteger, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ===================== 用户域 =====================

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ===================== 公司基础域 =====================

class StockBasic(Base):
    """股票基础信息。code 格式为 6位数字，market 字段区分 SH/SZ/BJ。"""
    __tablename__ = "stock_basic"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), unique=True, index=True, comment="股票代码 000625")
    market: Mapped[str] = mapped_column(String(6), comment="SH/SZ/BJ")
    secucode: Mapped[str] = mapped_column(String(12), unique=True, comment="东财代码 SZ000625")
    stock_name: Mapped[str] = mapped_column(String(50), index=True)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_st: Mapped[bool] = mapped_column(Boolean, default=False)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def secucode_format(self) -> str:
        return f"{self.market}{self.stock_code}"


class Watchlist(Base):
    """自选股，按 user_id 隔离。"""
    __tablename__ = "stock_watchlist"
    __table_args__ = (UniqueConstraint("user_id", "stock_code", name="uk_user_stock"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    stock_name: Mapped[str] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    add_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ===================== 财务核心域 =====================

class FinReport(Base):
    """财务报表（三表合一）。

    设计思路：
    - balance_json / income_json / cashflow_json 存储东方财富接口返回的原始字段（完整不丢数据）
    - 关键指标直接存列，用于自选股列表/对比页排序与概览
    - 单条记录 = 某股票某报告期
    """
    __tablename__ = "fin_report"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_stock_report"),
        Index("ix_fin_report_date", "report_date"),
        Index("ix_fin_report_stock_date", "stock_code", "report_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date, comment="报告期")
    report_type: Mapped[str] = mapped_column(String(10), comment="Q1/H1/Q3/Annual")
    report_name: Mapped[str] = mapped_column(String(20), comment="2025年报")
    notice_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="公告日期")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # ---- 原始数据 (东财原始字段，JSON) ----
    balance_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="资产负债表原始数据")
    income_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="利润表原始数据")
    cashflow_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="现金流量表原始数据")

    # ---- 关键指标（提取列，用于列表/排序） ----
    # 规模
    total_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="总资产(元)")
    total_liabilities: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="总负债(元)")
    total_equity: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="股东权益合计(元)")
    total_revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="营业总收入(元)")
    operate_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="营业利润(元)")
    total_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="利润总额(元)")
    net_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="净利润(元)")
    net_profit_parent: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="归母净利润(元)")
    deduct_net_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="扣非净利润(元)")
    operate_cash_net: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True, comment="经营活动现金流净额(元)")

    # 每股指标
    eps: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="基本每股收益(元)")
    bps: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="每股净资产(元)")
    capital_reserve_ps: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="每股资本公积(元)")
    undistr_profit_ps: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="每股未分配利润(元)")

    # 盈利能力
    roe: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="净资产收益率ROE(%)")
    roa: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="总资产收益率ROA(%)")
    gross_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="销售毛利率(%)")
    net_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="销售净利率(%)")

    # 偿债能力
    debt_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="资产负债率(%)")
    current_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="流动比率")
    quick_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="速动比率")

    # 成长能力（同比）
    revenue_yoy: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="营收同比(%)")
    net_profit_yoy: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="净利润同比(%)")
    assets_yoy: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="总资产同比(%)")


class FinMainIndicator(Base):
    """主要财务指标（东财财务分析-主要指标页），单独存储。"""
    __tablename__ = "fin_main_indicator"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_stock_report"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date)
    report_type: Mapped[str] = mapped_column(String(10))
    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


# ===================== 公告域 =====================

class Announcement(Base):
    """上市公司公告。"""
    __tablename__ = "ann_announcement"
    __table_args__ = (
        Index("idx_stock_publish", "stock_code", "publish_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    ann_title: Mapped[str] = mapped_column(String(300))
    ann_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    publish_date: Mapped[date] = mapped_column(Date)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="eastmoney")
    fetch_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ===================== 辅助表 =====================

class CollectTaskLog(Base):
    """采集进度日志。"""
    __tablename__ = "collect_task_log"
    __table_args__ = (
        UniqueConstraint("stock_code", "task_type", name="uk_stock_task"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    task_type: Mapped[str] = mapped_column(String(30), comment="balance/income/cashflow/indicator/basic")
    status: Mapped[str] = mapped_column(String(10), default="pending", comment="pending/collecting/done/failed")
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_attempt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    report_count: Mapped[int] = mapped_column(Integer, default=0, comment="本次采集的报告期数量")
