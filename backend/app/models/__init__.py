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
    sina_code: Mapped[str | None] = mapped_column(String(15), comment="新浪接口代码 sh600519")
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
