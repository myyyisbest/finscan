"""SQLAlchemy 数据模型 - Finscan Pro"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Text,
    DECIMAL, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column

Base = declarative_base()


class Stock(Base):
    """股票基本信息"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(12), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    full_name = Column(String(200))
    industry = Column(String(50), index=True)
    sub_industry = Column(String(50))
    market = Column(String(10))
    list_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    audit_records = relationship("AuditRecord", back_populates="stock", cascade="all, delete-orphan")
    income_statements = relationship("IncomeStatement", back_populates="stock", cascade="all, delete-orphan")
    balance_sheets = relationship("BalanceSheet", back_populates="stock", cascade="all, delete-orphan")
    cashflow_statements = relationship("CashflowStatement", back_populates="stock", cascade="all, delete-orphan")
    financial_indicators = relationship("FinancialIndicator", back_populates="stock", cascade="all, delete-orphan")
    finscan_reports = relationship("FinscanReport", back_populates="stock", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="stock", cascade="all, delete-orphan")


class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    watchlist_groups = relationship("WatchlistGroup", back_populates="user", cascade="all, delete-orphan")


class WatchlistGroup(Base):
    """自选分组"""
    __tablename__ = "watchlist_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="watchlist_groups")
    items = relationship("WatchlistItem", back_populates="group_", cascade="all, delete-orphan")


class WatchlistItem(Base):
    """自选股"""
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("watchlist_groups.id", ondelete="CASCADE"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    alert_enabled = Column(Boolean, default=True)

    group_ = relationship("WatchlistGroup", back_populates="items")
    stock = relationship("Stock")

    __table_args__ = (UniqueConstraint("group_id", "stock_id"),)


class AuditRecord(Base):
    """审计信息"""
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    end_date = Column(Date, nullable=False)
    ann_date = Column(Date, nullable=False)
    audit_result = Column(String(50), nullable=False)
    audit_agency = Column(String(100))
    audit_fees = Column(DECIMAL(18, 2))

    stock = relationship("Stock", back_populates="audit_records")

    __table_args__ = (UniqueConstraint("stock_id", "end_date"),)


class IncomeStatement(Base):
    """利润表"""
    __tablename__ = "income_statements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    end_date = Column(Date, nullable=False)
    report_type = Column(String(10), nullable=False)  # 年度/中期/季度

    # 金额字段
    revenue = Column(DECIMAL(24, 2))
    revenue_yoy = Column(DECIMAL(12, 4))
    oper_cost = Column(DECIMAL(24, 2))
    gross_profit = Column(DECIMAL(24, 2))
    sell_exp = Column(DECIMAL(24, 2))
    admin_exp = Column(DECIMAL(24, 2))
    rd_exp = Column(DECIMAL(24, 2))
    fin_exp = Column(DECIMAL(24, 2))
    assets_impair_loss = Column(DECIMAL(24, 2))
    credit_impa_loss = Column(DECIMAL(24, 2))
    oth_biz_income = Column(DECIMAL(24, 2))
    invest_income = Column(DECIMAL(24, 2))
    operate_profit = Column(DECIMAL(24, 2))
    net_profit = Column(DECIMAL(24, 2))
    n_income_attr_p = Column(DECIMAL(24, 2))
    deduct_non_recurring = Column(DECIMAL(24, 2))
    basic_eps = Column(DECIMAL(12, 4))

    stock = relationship("Stock", back_populates="income_statements")

    __table_args__ = (UniqueConstraint("stock_id", "end_date", "report_type"),)


class BalanceSheet(Base):
    """资产负债表"""
    __tablename__ = "balance_sheets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    end_date = Column(Date, nullable=False)
    report_type = Column(String(10), nullable=False)

    total_assets = Column(DECIMAL(24, 2))
    total_liab = Column(DECIMAL(24, 2))
    total_hldr_eqy_exc_min_int = Column(DECIMAL(24, 2))
    money_cap = Column(DECIMAL(24, 2))
    accounts_receiv = Column(DECIMAL(24, 2))
    oth_receiv = Column(DECIMAL(24, 2))
    inventories = Column(DECIMAL(24, 2))
    total_current_assets = Column(DECIMAL(24, 2))
    fix_assets = Column(DECIMAL(24, 2))
    cip = Column(DECIMAL(24, 2))
    goodwill = Column(DECIMAL(24, 2))
    lt_amort_deferred_exp = Column(DECIMAL(24, 2))
    intang_assets = Column(DECIMAL(24, 2))
    st_borr = Column(DECIMAL(24, 2))
    lt_borr = Column(DECIMAL(24, 2))
    bond_payable = Column(DECIMAL(24, 2))
    accounts_payable = Column(DECIMAL(24, 2))
    advance_receipts = Column(DECIMAL(24, 2))
    contract_liab = Column(DECIMAL(24, 2))
    total_current_liab = Column(DECIMAL(24, 2))

    stock = relationship("Stock", back_populates="balance_sheets")

    __table_args__ = (UniqueConstraint("stock_id", "end_date", "report_type"),)


class CashflowStatement(Base):
    """现金流量表"""
    __tablename__ = "cashflow_statements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    end_date = Column(Date, nullable=False)
    report_type = Column(String(10), nullable=False)

    n_cashflow_act = Column(DECIMAL(24, 2))
    n_cashflow_inv_act = Column(DECIMAL(24, 2))
    n_cash_flows_fnc_act = Column(DECIMAL(24, 2))
    c_recp_prov_sg_act = Column(DECIMAL(24, 2))
    c_pay_acq_const_fiolta = Column(DECIMAL(24, 2))
    free_cashflow = Column(DECIMAL(24, 2))

    stock = relationship("Stock", back_populates="cashflow_statements")

    __table_args__ = (UniqueConstraint("stock_id", "end_date", "report_type"),)


class FinancialIndicator(Base):
    """财务指标"""
    __tablename__ = "financial_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    end_date = Column(Date, nullable=False)
    report_type = Column(String(10), nullable=False)

    # 盈利能力
    roe = Column(DECIMAL(12, 4))
    roe_deducted = Column(DECIMAL(12, 4))
    roic = Column(DECIMAL(12, 4))
    grossprofit_margin = Column(DECIMAL(12, 4))
    netprofit_margin = Column(DECIMAL(12, 4))
    core_profit_ratio = Column(DECIMAL(12, 4))

    # 成长能力
    revenue_yoy = Column(DECIMAL(12, 4))
    netprofit_yoy = Column(DECIMAL(12, 4))

    # 营运能力
    inv_turn = Column(DECIMAL(12, 4))
    ar_turn = Column(DECIMAL(12, 4))
    assets_turn = Column(DECIMAL(12, 4))
    current_ratio = Column(DECIMAL(12, 4))
    quick_ratio = Column(DECIMAL(12, 4))

    # 偿债能力
    debt_to_assets = Column(DECIMAL(12, 4))

    # 现金流
    cash_to_debt = Column(DECIMAL(12, 4))
    fcff = Column(DECIMAL(24, 2))

    # 每股指标
    bps = Column(DECIMAL(18, 4))
    eps = Column(DECIMAL(12, 4))
    oper_cash_flow_per_share = Column(DECIMAL(18, 4))

    # 估值
    pe_ttm = Column(DECIMAL(12, 4))
    pb = Column(DECIMAL(12, 4))
    ps = Column(DECIMAL(12, 4))

    stock = relationship("Stock", back_populates="financial_indicators")

    __table_args__ = (UniqueConstraint("stock_id", "end_date", "report_type"),)


class FinscanReport(Base):
    """排雷报告"""
    __tablename__ = "finscan_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    report_year = Column(Integer, nullable=False)
    total_score = Column(DECIMAL(8, 2), default=0)
    risk_level = Column(String(20))  # LOW/MEDIUM/HIGH/VERY_HIGH/REJECT
    n_pass = Column(Integer, default=0)
    n_warn = Column(Integer, default=0)
    n_fail = Column(Integer, default=0)
    n_skip = Column(Integer, default=0)
    combo_bonus = Column(Integer, default=0)
    data_source = Column(String(20))
    pdf_used = Column(Boolean, default=False)
    fin_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock", back_populates="finscan_reports")
    user = relationship("User")
    rule_results = relationship("RuleResult", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("stock_id", "report_year"),)


class RuleResult(Base):
    """规则结果"""
    __tablename__ = "rule_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("finscan_reports.id", ondelete="CASCADE"), nullable=False)
    layer = Column(Integer, nullable=False)
    rule_code = Column(String(10), nullable=False)
    rule_name = Column(String(100), nullable=False)
    verdict = Column(String(10), nullable=False)  # PASS/WARN/FAIL/SKIP
    score_added = Column(DECIMAL(8, 2), default=0)
    detail = Column(Text)
    raw_values = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("FinscanReport", back_populates="rule_results")


class Announcement(Base):
    """公告"""
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    ann_date = Column(Date, nullable=False)
    ann_time = Column(DateTime)
    category = Column(String(50))  # 定期报告/业绩预告/重大事项等
    url = Column(String(500))
    is_key = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock", back_populates="announcements")


class CollectTask(Base):
    """采集任务"""
    __tablename__ = "collect_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")  # pending/running/done/failed
    error_msg = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class PeerIndicator(Base):
    """同行对比指标"""
    __tablename__ = "peer_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    peer_stock_id = Column(Integer, ForeignKey("stocks.id"))
    end_date = Column(Date, nullable=False)
    grossprofit_margin = Column(DECIMAL(12, 4))
    netprofit_margin = Column(DECIMAL(12, 4))
    roe = Column(DECIMAL(12, 4))
    debt_to_assets = Column(DECIMAL(12, 4))
    inv_turn = Column(DECIMAL(12, 4))
    ar_turn = Column(DECIMAL(12, 4))

    __table_args__ = (UniqueConstraint("stock_id", "peer_stock_id", "end_date"),)
