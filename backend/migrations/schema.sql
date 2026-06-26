-- Finscan Pro 数据库 Schema
-- 支持 SQLite（开发）和 PostgreSQL（生产）
-- 创建时间: 2026-06-26

-- ============================================
-- 基础层：股票与用户
-- ============================================

-- 股票基本信息
CREATE TABLE IF NOT EXISTS stocks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code         VARCHAR(12) UNIQUE NOT NULL,
    name            VARCHAR(100) NOT NULL,
    full_name       VARCHAR(200),
    industry        VARCHAR(50),
    sub_industry    VARCHAR(50),
    market          VARCHAR(10),
    list_date       DATE,
    is_active       BOOLEAN DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stocks_name ON stocks(name);
CREATE INDEX IF NOT EXISTS idx_stocks_industry ON stocks(industry);

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(100) UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 自选分组
CREATE TABLE IF NOT EXISTS watchlist_groups (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 自选股关联
CREATE TABLE IF NOT EXISTS watchlist_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id        INTEGER REFERENCES watchlist_groups(id) ON DELETE CASCADE,
    stock_id        INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_enabled   BOOLEAN DEFAULT 1,
    UNIQUE(group_id, stock_id)
);

-- ============================================
-- 财务数据层：三表 + 指标
-- ============================================

-- 年报审计信息
CREATE TABLE IF NOT EXISTS audit_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,
    ann_date        DATE NOT NULL,
    audit_result    VARCHAR(50) NOT NULL,
    audit_agency    VARCHAR(100),
    audit_fees      DECIMAL(18,2),
    UNIQUE(stock_id, end_date)
);

CREATE INDEX IF NOT EXISTS idx_audit_stock_date ON audit_records(stock_id, end_date DESC);

-- 利润表
CREATE TABLE IF NOT EXISTS income_statements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,
    report_type     VARCHAR(10) NOT NULL,
    -- 单位：元
    revenue                 DECIMAL(24,2),
    revenue_yoy             DECIMAL(12,4),
    oper_cost               DECIMAL(24,2),
    gross_profit            DECIMAL(24,2),
    sell_exp                DECIMAL(24,2),
    admin_exp               DECIMAL(24,2),
    rd_exp                  DECIMAL(24,2),
    fin_exp                 DECIMAL(24,2),
    assets_impair_loss      DECIMAL(24,2),
    credit_impa_loss        DECIMAL(24,2),
    oth_biz_income          DECIMAL(24,2),
    invest_income           DECIMAL(24,2),
    operate_profit          DECIMAL(24,2),
    net_profit              DECIMAL(24,2),
    n_income_attr_p         DECIMAL(24,2),
    deduct_non_recurring    DECIMAL(24,2),
    basic_eps               DECIMAL(12,4),
    UNIQUE(stock_id, end_date, report_type)
);

CREATE INDEX IF NOT EXISTS idx_income_stock_date ON income_statements(stock_id, end_date DESC);

-- 资产负债表
CREATE TABLE IF NOT EXISTS balance_sheets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,
    report_type     VARCHAR(10) NOT NULL,
    total_assets                DECIMAL(24,2),
    total_liab                  DECIMAL(24,2),
    total_hldr_eqy_exc_min_int  DECIMAL(24,2),
    money_cap                   DECIMAL(24,2),
    accounts_receiv             DECIMAL(24,2),
    oth_receiv                  DECIMAL(24,2),
    inventories                 DECIMAL(24,2),
    total_current_assets        DECIMAL(24,2),
    fix_assets                  DECIMAL(24,2),
    cip                         DECIMAL(24,2),
    goodwill                    DECIMAL(24,2),
    lt_amort_deferred_exp       DECIMAL(24,2),
    intang_assets               DECIMAL(24,2),
    st_borr                     DECIMAL(24,2),
    lt_borr                     DECIMAL(24,2),
    bond_payable                DECIMAL(24,2),
    accounts_payable            DECIMAL(24,2),
    advance_receipts            DECIMAL(24,2),
    contract_liab               DECIMAL(24,2),
    total_current_liab          DECIMAL(24,2),
    UNIQUE(stock_id, end_date, report_type)
);

CREATE INDEX IF NOT EXISTS idx_balance_stock_date ON balance_sheets(stock_id, end_date DESC);

-- 现金流量表
CREATE TABLE IF NOT EXISTS cashflow_statements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,
    report_type     VARCHAR(10) NOT NULL,
    n_cashflow_act          DECIMAL(24,2),
    n_cashflow_inv_act      DECIMAL(24,2),
    n_cash_flows_fnc_act    DECIMAL(24,2),
    c_recp_prov_sg_act      DECIMAL(24,2),
    c_pay_acq_const_fiolta  DECIMAL(24,2),
    free_cashflow            DECIMAL(24,2),
    UNIQUE(stock_id, end_date, report_type)
);

CREATE INDEX IF NOT EXISTS idx_cashflow_stock_date ON cashflow_statements(stock_id, end_date DESC);

-- 财务指标
CREATE TABLE IF NOT EXISTS financial_indicators (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,
    report_type     VARCHAR(10) NOT NULL,
    -- 盈利能力
    roe                     DECIMAL(12,4),
    roe_deducted            DECIMAL(12,4),
    roic                    DECIMAL(12,4),
    grossprofit_margin       DECIMAL(12,4),
    netprofit_margin        DECIMAL(12,4),
    core_profit_ratio       DECIMAL(12,4),
    -- 成长能力
    revenue_yoy             DECIMAL(12,4),
    netprofit_yoy           DECIMAL(12,4),
    -- 营运能力
    inv_turn                DECIMAL(12,4),
    ar_turn                 DECIMAL(12,4),
    assets_turn             DECIMAL(12,4),
    current_ratio           DECIMAL(12,4),
    quick_ratio             DECIMAL(12,4),
    -- 偿债能力
    debt_to_assets          DECIMAL(12,4),
    -- 现金流
    cash_to_debt            DECIMAL(12,4),
    fcff                    DECIMAL(24,2),
    -- 每股指标
    bps                     DECIMAL(18,4),
    eps                     DECIMAL(12,4),
    oper_cash_flow_per_share DECIMAL(18,4),
    -- 估值
    pe_ttm                  DECIMAL(12,4),
    pb                      DECIMAL(12,4),
    ps                      DECIMAL(12,4),
    UNIQUE(stock_id, end_date, report_type)
);

CREATE INDEX IF NOT EXISTS idx_indicator_stock_date ON financial_indicators(stock_id, end_date DESC);

-- ============================================
-- 排雷分析层
-- ============================================

-- 排雷报告主表
CREATE TABLE IF NOT EXISTS finscan_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    user_id         INTEGER REFERENCES users(id),
    report_year     INTEGER NOT NULL,
    total_score     DECIMAL(8,2) DEFAULT 0,
    risk_level      VARCHAR(20),
    n_pass          INTEGER DEFAULT 0,
    n_warn          INTEGER DEFAULT 0,
    n_fail          INTEGER DEFAULT 0,
    n_skip          INTEGER DEFAULT 0,
    combo_bonus     INTEGER DEFAULT 0,
    data_source     VARCHAR(20),
    pdf_used        BOOLEAN DEFAULT 0,
    fin_summary     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, report_year)
);

CREATE INDEX IF NOT EXISTS idx_report_stock ON finscan_reports(stock_id);
CREATE INDEX IF NOT EXISTS idx_report_score ON finscan_reports(total_score);

-- 规则结果明细
CREATE TABLE IF NOT EXISTS rule_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id       INTEGER REFERENCES finscan_reports(id) ON DELETE CASCADE,
    layer           INTEGER NOT NULL,
    rule_code       VARCHAR(10) NOT NULL,
    rule_name       VARCHAR(100) NOT NULL,
    verdict         VARCHAR(10) NOT NULL,
    score_added     DECIMAL(8,2) DEFAULT 0,
    detail          TEXT,
    raw_values      TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rule_report ON rule_results(report_id);

-- ============================================
-- 公告与资讯层
-- ============================================

-- 公告索引
CREATE TABLE IF NOT EXISTS announcements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    title           VARCHAR(500) NOT NULL,
    ann_date        DATE NOT NULL,
    ann_time        TIMESTAMP,
    category        VARCHAR(50),
    url             VARCHAR(500),
    is_key          BOOLEAN DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ann_stock_date ON announcements(stock_id, ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_ann_category ON announcements(category);

-- ============================================
-- 任务队列
-- ============================================

CREATE TABLE IF NOT EXISTS collect_tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id),
    task_type       VARCHAR(50) NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',
    error_msg       TEXT,
    started_at      TIMESTAMP,
    finished_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 同行对比数据
-- ============================================

CREATE TABLE IF NOT EXISTS peer_indicators (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    peer_stock_id   INTEGER REFERENCES stocks(id),
    end_date        DATE NOT NULL,
    grossprofit_margin  DECIMAL(12,4),
    netprofit_margin    DECIMAL(12,4),
    roe                 DECIMAL(12,4),
    debt_to_assets      DECIMAL(12,4),
    inv_turn            DECIMAL(12,4),
    ar_turn             DECIMAL(12,4),
    UNIQUE(stock_id, peer_stock_id, end_date)
);
