"""SQLAlchemy ORM 模型 —— 按业务域组织。

基于 PRD 第三节 schema，并落实批次0/评审的修正：
  - 新增 user 表 + 鉴权，关注池按 user_id 隔离
  - 新增 industry_indicator_median 行业中位值表(规则1.1/对标页依赖)
  - 新增 collect_task_log 采集进度表(断点续传)
  - report_type 用英文枚举 Q1/H1/Q3/Annual
  - 金额 DECIMAL(20,4)，比率 DECIMAL(10,4)
  - 采集范围覆盖近 6 年

注: SQLite 不真正限制 DECIMAL 精度，但语义一致；切 MariaDB 后精度生效。
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Integer, String, Text, DECIMAL, Date, DateTime, Boolean,
    ForeignKey, Index, UniqueConstraint, SmallInteger,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ===================== 用户域 =====================

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="用户名")
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否管理员")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ===================== 公司基础域 =====================

class StockBasic(Base):
    __tablename__ = "stock_basic"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), unique=True, index=True, comment="股票代码 600519.SH")
    stock_name: Mapped[str] = mapped_column(String(50), index=True, comment="股票简称")
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(50), index=True, comment="申万一级行业")
    market: Mapped[str | None] = mapped_column(String(20), comment="主板/创业板/科创板/北交所")
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_st: Mapped[bool] = mapped_column(Boolean, default=False)
    # EM 东方财富代码: 1.600879 / 0.300136
    em_code: Mapped[str | None] = mapped_column(String(15), comment="EM 代码 1.600879")
    # 股本(EM)
    total_share: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="总股本(股)")
    float_share: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="流通股本(股)")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class StockRealtimeQuote(Base):
    """实时行情快照 —— EM 东方财富提供 PE/PB/市值/涨跌幅。

    按 (stock_code, quote_date) 唯一键 upsert。
    """
    __tablename__ = "stock_realtime_quote"
    __table_args__ = (
        UniqueConstraint("stock_code", "quote_date", name="uk_quote_stock_date"),
        Index("ix_quote_date", "quote_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    quote_date: Mapped[date] = mapped_column(Date, comment="行情日期")
    # 价格
    latest_price: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="最新价")
    open_price: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True)
    pre_close: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True)
    change_pct: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="涨跌幅%")
    change_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="涨跌额")
    volume: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="成交量(手)")
    turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="成交额(元)")
    # 估值
    pe_dynamic: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="动态市盈率")
    pe_ttm: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="TTM 市盈率")
    pb: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="市净率")
    ps_ttm: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="市销率")
    # 市值
    total_market_cap: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="总市值(元)")
    float_market_cap: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="流通市值(元)")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Watchlist(Base):
    """关注池，按 user_id 隔离"""
    __tablename__ = "stock_watchlist"
    __table_args__ = (UniqueConstraint("user_id", "group_name", "stock_code", name="uk_user_group_stock"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True)
    group_name: Mapped[str] = mapped_column(String(50), default="默认分组", index=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    stock_name: Mapped[str] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    add_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ===================== 财务核心域 =====================

def _fin_common():
    """三大报表/指标公共列的列定义工厂，减少重复。"""
    return None

class BalanceSheet(Base):
    __tablename__ = "fin_balance_sheet"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_stock_report"),
        Index("ix_fin_balance_sheet_report_date", "report_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date, comment="报告期")
    report_type: Mapped[str] = mapped_column(String(10), comment="Q1/H1/Q3/Annual")
    # 资产
    total_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    total_current_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    monetary_funds: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    accounts_receivable: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    inventory: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    total_noncurrent_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    fixed_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    construction_in_progress: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    intangible_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    goodwill: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    long_deferred_expenses: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    # 负债
    total_liabilities: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    total_current_liabilities: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    short_term_borrowings: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    accounts_payable: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    total_noncurrent_liabilities: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    long_term_borrowings: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    bonds_payable: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    # 权益
    total_equity: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    share_capital: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    capital_reserve: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    retained_profits: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    other_receivables: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class IncomeStatement(Base):
    __tablename__ = "fin_income_statement"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_fin_income_statement_stock_report"),
        Index("ix_fin_income_statement_report_date", "report_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date)
    report_type: Mapped[str] = mapped_column(String(10))
    total_revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    operating_cost: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    gross_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="=营收-成本")
    gross_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="毛利率%")
    selling_expenses: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    admin_expenses: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    rd_expenses: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    financial_expenses: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    operating_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    total_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    net_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    net_profit_parent: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="归母净利润")
    net_profit_deduct: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="扣非")
    asset_impairment_loss: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    other_income: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    investment_income: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class CashFlow(Base):
    __tablename__ = "fin_cash_flow"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_fin_cash_flow_stock_report"),
        Index("ix_fin_cash_flow_report_date", "report_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date)
    report_type: Mapped[str] = mapped_column(String(10))
    operating_cash_inflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    operating_cash_outflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    operating_cash_net: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    sales_cash_received: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    investing_cash_net: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    financing_cash_net: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    capital_expenditure: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="资本开支")
    free_cash_flow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="=经营净额-资本开支")
    cash_ending_balance: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class FinIndicator(Base):
    """衍生财务指标 —— 口径来自东财预计算值，统一可比。

    口径说明:
      ROE = 归母净利润 / 平均净资产(东财值)
      周转率 = 营业收入或成本 / 平均余额(东财值)
      ap_turnover 由本系统计算 = 营业成本 / 平均应付账款
    """
    __tablename__ = "fin_indicators"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_fin_indicators_stock_report"),
        Index("ix_fin_indicators_report_date", "report_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date)
    report_type: Mapped[str] = mapped_column(String(10))
    roe: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="净资产收益率%")
    roa: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="总资产收益率%")
    net_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="净利率%")
    debt_to_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="资产负债率%")
    current_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    quick_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    ar_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="应收账款周转率")
    inventory_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    total_asset_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    operating_cycle: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True, comment="营业周期天")
    ap_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="应付账款周转率(自算)")
    revenue_yoy: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="营收同比%")
    net_profit_yoy: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="净利润同比%")
    cf_to_net_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="经营现金流/净利润")
    sales_cash_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="销售收现比")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class FinMainIndicator(Base):
    """东财『主要指标』全量 —— 来自新浪 stock_financial_analysis_indicator 预计算。

    一次性覆盖 EM 财务分析页 主要指标 / 杜邦分析 / 财务风险 / 营运能力 等 80+ 指标。
    报告期: 季度，按 (stock_code, report_date) 唯一。
    """
    __tablename__ = "fin_main_indicators"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_fin_main_stock_report"),
        Index("ix_fin_main_indicators_report_date", "report_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date)
    report_type: Mapped[str] = mapped_column(String(10), comment="Q1/H1/Q3/Annual")

    # ===== 每股指标 =====
    eps_basic: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="基本每股收益(元)")
    eps_diluted: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="稀释每股收益(元)")
    eps_weighted: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="加权每股收益(元)")
    eps_adj: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="调整后每股收益(元)")
    eps_deduct: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="扣非每股收益(元)")
    bps: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="每股净资产(元)")
    bps_adj: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="调整后每股净资产(元)")
    ocfps: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="每股经营现金流(元)")
    capital_reserve_per_share: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="每股资本公积金(元)")
    retained_eps: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True, comment="每股未分配利润(元)")

    # ===== 规模(元) =====
    main_revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="主营业务收入")
    main_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="主营业务利润")
    net_profit_deduct: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="扣非净利润(元)")
    total_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True, comment="总资产(元)")

    # ===== 成长性 % =====
    revenue_yoy: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="主营收入增长率%")
    net_profit_yoy: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="净利润增长率%")
    equity_yoy: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="净资产增长率%")
    total_asset_yoy: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="总资产增长率%")

    # ===== 盈利能力 % =====
    roe: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="净资产收益率%")
    roe_weighted: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="加权净资产收益率%")
    roa: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="总资产利润率%")
    roa_net: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="总资产净利润率%")
    net_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="销售净利率%")
    gross_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="销售毛利率%")
    main_profit_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="主营业务利润率%")
    op_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="营业利润率%")
    cost_to_expense_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="成本费用利润率%")
    dividend_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="股息发放率%")

    # ===== 收益质量 % =====
    sales_cash_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="经营现金净流量/销售收入%")
    cf_to_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="资产的经营现金流量回报率%")
    cf_to_net_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="经营现金净流量/净利润%")
    cf_to_debt: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="经营现金净流量/负债%")

    # ===== 偿债能力 =====
    current_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="流动比率")
    quick_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="速动比率")
    cash_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="现金比率%")
    cash_flow_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="现金流量比率%")
    debt_to_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="资产负债率%")
    equity_multiplier: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="权益乘数(负债与所有者权益比率%)")
    debt_to_equity: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="产权比率%")
    equity_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="股东权益比率%")
    long_debt_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="长期负债比率%")
    fixed_asset_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="固定资产比重%")

    # ===== 营运能力 =====
    ar_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="应收账款周转率(次)")
    ar_turnover_days: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="应收账款周转天数(天)")
    inventory_turnover_days: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="存货周转天数(天)")
    inventory_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="存货周转率(次)")
    fixed_asset_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="固定资产周转率(次)")
    total_asset_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="总资产周转率(次)")
    total_asset_turnover_days: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="总资产周转天数(天)")
    current_asset_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="流动资产周转率(次)")
    current_asset_turnover_days: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="流动资产周转天数(天)")
    equity_turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="股东权益周转率(次)")

    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


# ===================== 附注域 =====================

class NoteMainBusiness(Base):
    __tablename__ = "note_main_business"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "biz_type", "biz_name", name="uk_stock_report_biz"),
        Index("ix_note_main_business_stock_report", "stock_code", "report_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date)
    biz_type: Mapped[str] = mapped_column(String(20), comment="产品/行业/地区")
    biz_name: Mapped[str] = mapped_column(String(100))
    revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    gross_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    gross_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    revenue_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True, comment="收入占比%")
    fetch_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ===================== 公告域 =====================

class Announcement(Base):
    __tablename__ = "ann_announcement"
    __table_args__ = (
        UniqueConstraint("stock_code", "pdf_url", name="uk_stock_pdf"),
        Index("idx_stock_publish", "stock_code", "publish_date"),
        Index("idx_type", "ann_type"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    ann_title: Mapped[str] = mapped_column(String(200))
    ann_type: Mapped[str] = mapped_column(String(30), comment="定期报告/业绩预告/并购重组/监管问询/分红派息/其他")
    publish_date: Mapped[date] = mapped_column(Date)
    pdf_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="巨潮")
    fetch_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ===================== 排雷域 =====================

class RiskRule(Base):
    __tablename__ = "risk_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_code: Mapped[str] = mapped_column(String(10), unique=True, comment="规则编号 1.1")
    rule_name: Mapped[str] = mapped_column(String(100))
    rule_layer: Mapped[int] = mapped_column(SmallInteger, comment="层级 0-6")
    rule_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    warn_threshold: Mapped[str | None] = mapped_column(Text, nullable=True, comment="JSON")
    fail_threshold: Mapped[str | None] = mapped_column(Text, nullable=True, comment="JSON")
    warn_score: Mapped[Decimal] = mapped_column(DECIMAL(3, 1), default=Decimal("2"))
    fail_score: Mapped[Decimal] = mapped_column(DECIMAL(3, 1), default=Decimal("5"))
    data_source: Mapped[str] = mapped_column(String(20), comment="sina/em/announcement")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class RiskReport(Base):
    __tablename__ = "risk_report"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_risk_report_stock_report"),
        Index("idx_risk_level", "risk_level"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date)
    total_score: Mapped[Decimal] = mapped_column(DECIMAL(5, 1), comment="总风险得分")
    risk_level: Mapped[str] = mapped_column(String(10), comment="低/中/高/极高/直接排除")
    rule_total: Mapped[int] = mapped_column(Integer)
    rule_participated: Mapped[int] = mapped_column(Integer)
    data_completeness: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), comment="数据完整度%")
    calc_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RiskRuleResult(Base):
    __tablename__ = "risk_rule_result"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "rule_code", name="uk_stock_rule"),
        Index("ix_risk_rule_result_stock_report", "stock_code", "report_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    report_date: Mapped[date] = mapped_column(Date)
    rule_code: Mapped[str] = mapped_column(String(10))
    result: Mapped[str] = mapped_column(String(10), comment="PASS/WARN/FAIL/SKIP")
    score: Mapped[Decimal] = mapped_column(DECIMAL(3, 1), default=Decimal("0"))
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True, comment="判定证据")
    calc_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ===================== 辅助表（评审修正项）=====================

class IndustryIndicatorMedian(Base):
    """行业中位值预计算表 —— 规则1.1(同行对比)、对标页(行业中位值参考线)依赖。"""
    __tablename__ = "industry_indicator_median"
    __table_args__ = (
        UniqueConstraint("industry", "report_date", "indicator_code", name="uk_industry_date_ind"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry: Mapped[str] = mapped_column(String(50), index=True, comment="申万一级行业")
    report_date: Mapped[date] = mapped_column(Date)
    indicator_code: Mapped[str] = mapped_column(String(30), comment="指标键 如 gross_margin")
    median_value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, comment="样本公司数")
    calc_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CollectTaskLog(Base):
    """采集进度表 —— 支持全量初始化的断点续传与失败重试。"""
    __tablename__ = "collect_task_log"
    __table_args__ = (
        UniqueConstraint("stock_code", "task_type", "report_date", name="uk_stock_task_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    task_type: Mapped[str] = mapped_column(String(20), comment="balance/income/cashflow/indicator/business")
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="pending", comment="pending/done/failed")
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_attempt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
