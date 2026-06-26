# Finscan Pro — 投研级财务分析平台

## 一、产品定位与愿景

**一句话定位**：面向专业投资者的投研级财务分析工具，以「财报排雷 + 深度分析 + 价值对比」为核心能力，区别于东方财富 F10 的行情导向，专注于基本面研究与风险识别。

**核心用户画像**：
- 价值投资者：重仓前必查财报风险
- 机构研究员：批量筛查自选池，快速定位异常标的
- 个人投资者：建立自己的投研数据库，避免踩雷

**差异化价值**：
- 不是选股工具，而是排雷工具——「财报是用来排除企业的」
- 不是数据堆砌，而是分析导向——「数据结构化、分析工具化」
- 不是固定模板，而是高度自定义——「分组、指标、规则全可配」

---

## 二、设计原则

### 视觉规范

| 维度 | 规范 |
|------|------|
| 主色调 | #1d4ed8（蓝）+ #ffffff（白）+ #f8fafc（灰白背景） |
| 风险色 | 绿 #52c41a / 黄 #faad14 / 橙 #fa8c16 / 红 #f5222d |
| 字体 | 主字体：-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei" |
| 间距 | 基础单位 8px，卡片间距 16px，内边距 20px |
| 圆角 | 卡片 8px，按钮 6px，输入框 6px |
| 阴影 | 卡片：`0 1px 3px rgba(0,0,0,0.1)`，hover：`0 4px 12px rgba(29,78,216,0.15)` |

### 交互规范

- 信息三级分层：核心概览 → 详细拆解 → 原始数据
- 默认展示高价值信息，次要内容折叠
- 异常数据自动高亮，点击可追溯原始科目
- 所有操作即时反馈，loading 状态明确

---

## 三、信息架构

```
┌──────────────────────────────────────────────────────────────────┐
│  顶部全局栏                                                         │
│  ┌─────────┐ ┌──────────────────────────┐ ┌──────┐ ┌────────┐  │
│  │ Logo    │ │ 🔍 全局搜索 (股票/公告)    │ │ 刷新 │ │ 用户   │  │
│  └─────────┘ └──────────────────────────┘ └──────┘ └────────┘  │
├────────┬─────────────────────────────────────────────────────────┤
│        │                                                          │
│ 左侧   │  主内容区                                                 │
│ 导航   │                                                          │
│        │  ┌─────────────────────────────────────────────────┐    │
│ ━━━━━  │  │                                                  │    │
│ 📊 自选 │  │           动态内容区 (卡片化布局)                 │    │
│ 📈 分析 │  │                                                  │    │
│ ⚠️ 排雷 │  │                                                  │    │
│ 📋 对比 │  └─────────────────────────────────────────────────┘    │
│ 📰 公告 │                                                          │
│ ⚙️ 设置 │                                                          │
│        │                                                          │
└────────┴─────────────────────────────────────────────────────────┘
```

### 功能模块

| 模块 | 入口 | 核心功能 |
|------|------|----------|
| **我的自选池** | 左侧导航首页 | 分组管理、批量筛查、快速排序、风险可视化 |
| **公司深度分析** | 搜索/自选点击 | Dashboard概览、财务报表、杜邦分析、现金流、经营构成、公司概况 |
| **财报排雷** | 左侧导航 | 规则扫描、风险评分、历史追踪、批量扫描 |
| **多标对比** | 左侧导航 | 最多4股同屏、维度自选、导出报告 |
| **公告中心** | 左侧导航 | 结构化分类、关键词检索、研报预期聚合 |

---

## 四、数据库设计

### 技术选型

**PostgreSQL** — 原因：
1. 支持 JSONB，可存储灵活的非结构化数据（如 PDF 解析结果）
2. 支持数组类型，适合多期数据存储
3. 成熟的并发连接池（pgBouncer 可水平扩展）
4. 强大的窗口函数，适合财务指标计算
5. 全文搜索支持，公告检索

### 核心表结构

```sql
-- ============================================
-- 基础层：股票与用户
-- ============================================

-- 股票基本信息
CREATE TABLE stocks (
    id              SERIAL PRIMARY KEY,
    ts_code         VARCHAR(12) UNIQUE NOT NULL,  -- 600519.SH / 002130.SZ
    name            VARCHAR(100) NOT NULL,
    full_name       VARCHAR(200),
    industry        VARCHAR(50),
    sub_industry    VARCHAR(50),                   -- 细分行业
    market          VARCHAR(10),                    -- SH/SZ/BJ
    list_date       DATE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_stocks_name ON stocks(name varchar_pattern_ops);
CREATE INDEX idx_stocks_industry ON stocks(industry);

-- 用户表
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(100) UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 自选分组
CREATE TABLE watchlist_groups (
    id              SERIAL PRIMARY KEY,
    user_id         INT REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL,
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 自选股关联
CREATE TABLE watchlist_items (
    id              SERIAL PRIMARY KEY,
    group_id        INT REFERENCES watchlist_groups(id) ON DELETE CASCADE,
    stock_id        INT REFERENCES stocks(id) ON DELETE CASCADE,
    added_at        TIMESTAMP DEFAULT NOW(),
    alert_enabled   BOOLEAN DEFAULT TRUE,
    UNIQUE(group_id, stock_id)
);

-- ============================================
-- 财务数据层：三表 + 指标
-- ============================================

-- 年报审计信息
CREATE TABLE audit_records (
    id              SERIAL PRIMARY KEY,
    stock_id        INT REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,                 -- 报告期截止日
    ann_date        DATE NOT NULL,                 -- 公告日期
    audit_result    VARCHAR(50) NOT NULL,         -- 标准无保留意见
    audit_agency    VARCHAR(100),                  -- 会计师事务所
    audit_fees      DECIMAL(18,2),                -- 审计费用(万元)
    UNIQUE(stock_id, end_date)
);

-- 利润表 (年度/季度)
CREATE TABLE income_statements (
    id              SERIAL PRIMARY KEY,
    stock_id        INT REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,
    report_type     VARCHAR(10) NOT NULL,          -- 年度/中期/季度
    -- 单位：元
    revenue                 DECIMAL(24,2),  -- 营业收入
    revenue_yoy             DECIMAL(12,4),  -- 营收YoY%
    oper_cost               DECIMAL(24,2),  -- 营业成本
    gross_profit            DECIMAL(24,2),  -- 毛利
    sell_exp                DECIMAL(24,2),  -- 销售费用
    admin_exp               DECIMAL(24,2),  -- 管理费用
    rd_exp                  DECIMAL(24,2),  -- 研发费用
    fin_exp                 DECIMAL(24,2),  -- 财务费用
    assets_impair_loss      DECIMAL(24,2),  -- 资产减值损失
    credit_impa_loss        DECIMAL(24,2),  -- 信用减值损失
    oth_biz_income          DECIMAL(24,2),  -- 其他业务收入
    invest_income            DECIMAL(24,2),  -- 投资收益
    operate_profit          DECIMAL(24,2),  -- 营业利润
    net_profit              DECIMAL(24,2),  -- 净利润
    n_income_attr_p         DECIMAL(24,2),  -- 归母净利润
    deduct_non_recurring     DECIMAL(24,2),  -- 扣非净利润
    basic_eps               DECIMAL(12,4),  -- 每股收益
    UNIQUE(stock_id, end_date, report_type)
);

CREATE INDEX idx_income_stock_date ON income_statements(stock_id, end_date DESC);

-- 资产负债表
CREATE TABLE balance_sheets (
    id              SERIAL PRIMARY KEY,
    stock_id        INT REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,
    report_type     VARCHAR(10) NOT NULL,
    -- 单位：元
    total_assets                DECIMAL(24,2),  -- 总资产
    total_liab                  DECIMAL(24,2),  -- 总负债
    total_hldr_eqy_exc_min_int  DECIMAL(24,2),  -- 归母净资产
    money_cap                   DECIMAL(24,2),  -- 货币资金
    accounts_receiv             DECIMAL(24,2),  -- 应收账款
    oth_receiv                  DECIMAL(24,2),  -- 其他应收款
    inventories                 DECIMAL(24,2),  -- 存货
    total_current_assets        DECIMAL(24,2),  -- 流动资产
    fix_assets                  DECIMAL(24,2),  -- 固定资产
    cip                         DECIMAL(24,2),  -- 在建工程
    goodwill                    DECIMAL(24,2),  -- 商誉
    lt_amort_deferred_exp       DECIMAL(24,2),  -- 长期待摊费用
    intang_assets               DECIMAL(24,2),  -- 无形资产
    st_borr                     DECIMAL(24,2),  -- 短期借款
    lt_borr                     DECIMAL(24,2),  -- 长期借款
    bond_payable                DECIMAL(24,2),  -- 应付债券
    accounts_payable            DECIMAL(24,2),  -- 应付账款
    advance_receipts            DECIMAL(24,2),  -- 预收款项
    contract_liab               DECIMAL(24,2),  -- 合同负债
    total_current_liab          DECIMAL(24,2),  -- 流动负债
    UNIQUE(stock_id, end_date, report_type)
);

CREATE INDEX idx_balance_stock_date ON balance_sheets(stock_id, end_date DESC);

-- 现金流量表
CREATE TABLE cashflow_statements (
    id              SERIAL PRIMARY KEY,
    stock_id        INT REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,
    report_type     VARCHAR(10) NOT NULL,
    -- 单位：元
    n_cashflow_act          DECIMAL(24,2),  -- 经营CF净额
    n_cashflow_inv_act      DECIMAL(24,2),  -- 投资CF净额
    n_cash_flows_fnc_act    DECIMAL(24,2),  -- 筹资CF净额
    c_recp_prov_sg_act      DECIMAL(24,2),  -- 销售收现
    c_pay_acq_const_fiolta  DECIMAL(24,2),  -- Capex
    free_cashflow            DECIMAL(24,2),  -- 自由现金流
    UNIQUE(stock_id, end_date, report_type)
);

CREATE INDEX idx_cashflow_stock_date ON cashflow_statements(stock_id, end_date DESC);

-- 财务指标
CREATE TABLE financial_indicators (
    id              SERIAL PRIMARY KEY,
    stock_id        INT REFERENCES stocks(id) ON DELETE CASCADE,
    end_date        DATE NOT NULL,
    report_type     VARCHAR(10) NOT NULL,
    -- 盈利能力
    roe                     DECIMAL(12,4),  -- ROE (%)
    roe_deducted            DECIMAL(12,4),  -- 扣非ROE (%)
    roic                    DECIMAL(12,4),  -- ROIC (%)
    grossprofit_margin       DECIMAL(12,4),  -- 毛利率 (%)
    netprofit_margin        DECIMAL(12,4),  -- 净利率 (%)
    core_profit_ratio       DECIMAL(12,4),  -- 核心利润占比 (%)
    -- 成长能力
    revenue_yoy             DECIMAL(12,4),  -- 营收YoY (%)
    netprofit_yoy           DECIMAL(12,4),  -- 净利润YoY (%)
    -- 营运能力
    inv_turn                DECIMAL(12,4),  -- 存货周转率
    ar_turn                 DECIMAL(12,4),  -- 应收周转率
    assets_turn             DECIMAL(12,4),  -- 总资产周转率
    current_ratio           DECIMAL(12,4),  -- 流动比率
    quick_ratio             DECIMAL(12,4),  -- 速动比率
    -- 偿债能力
    debt_to_assets          DECIMAL(12,4),  -- 资产负债率 (%)
    -- 现金流
    cash_to_debt            DECIMAL(12,4),  -- 货币资金/有息负债
    fcff                    DECIMAL(24,2),  -- 企业自由现金流
    -- 每股指标
    bps                     DECIMAL(18,4),  -- 每股净资产
    eps                     DECIMAL(12,4),  -- 每股收益
    oper_cash_flow_per_share DECIMAL(18,4), -- 每股经营CF
    -- 估值
    pe_ttm                  DECIMAL(12,4),  -- 市盈率TTM
    pb                      DECIMAL(12,4),  -- 市净率
    ps                      DECIMAL(12,4),  -- 市销率
    UNIQUE(stock_id, end_date, report_type)
);

CREATE INDEX idx_indicator_stock_date ON financial_indicators(stock_id, end_date DESC);

-- ============================================
-- 排雷分析层
-- ============================================

-- 排雷报告主表
CREATE TABLE finscan_reports (
    id              SERIAL PRIMARY KEY,
    stock_id        INT REFERENCES stocks(id) ON DELETE CASCADE,
    user_id         INT REFERENCES users(id),          -- 可为空（公开报告）
    report_year     INT NOT NULL,                      -- 分析年度
    total_score     DECIMAL(8,2) DEFAULT 0,            -- 总风险分
    risk_level      VARCHAR(20),                       -- LOW/MEDIUM/HIGH/VERY_HIGH/REJECT
    n_pass          INT DEFAULT 0,
    n_warn          INT DEFAULT 0,
    n_fail          INT DEFAULT 0,
    n_skip          INT DEFAULT 0,
    combo_bonus     INT DEFAULT 0,                     -- 组合加分
    data_source     VARCHAR(20),                       -- akshare/tushare
    pdf_used        BOOLEAN DEFAULT FALSE,
    fin_summary     JSONB,                             -- 财务摘要
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(stock_id, report_year)
);

CREATE INDEX idx_report_stock ON finscan_reports(stock_id);
CREATE INDEX idx_report_score ON finscan_reports(total_score);

-- 规则结果明细
CREATE TABLE rule_results (
    id              SERIAL PRIMARY KEY,
    report_id       INT REFERENCES finscan_reports(id) ON DELETE CASCADE,
    layer           INT NOT NULL,                      -- 0-6
    rule_code       VARCHAR(10) NOT NULL,              -- 1.1, 3.2, 4.1 等
    rule_name       VARCHAR(100) NOT NULL,
    verdict         VARCHAR(10) NOT NULL,              -- PASS/WARN/FAIL/SKIP
    score_added     DECIMAL(8,2) DEFAULT 0,
    detail          TEXT,                              -- 判定详情
    raw_values      JSONB,                             -- 原始计算数据
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rule_report ON rule_results(report_id);

-- ============================================
-- 公告与资讯层
-- ============================================

-- 公告索引
CREATE TABLE announcements (
    id              SERIAL PRIMARY KEY,
    stock_id        INT REFERENCES stocks(id) ON DELETE CASCADE,
    title           VARCHAR(500) NOT NULL,
    ann_date        DATE NOT NULL,
    ann_time        TIMESTAMP,
    category        VARCHAR(50),                       -- 定期报告/业绩预告/重大事项等
    url             VARCHAR(500),
    is_key          BOOLEAN DEFAULT FALSE,             -- 是否关键公告
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ann_stock_date ON announcements(stock_id, ann_date DESC);
CREATE INDEX idx_ann_category ON announcements(category);

-- ============================================
-- 同行对比数据
-- ============================================

CREATE TABLE peer_indicators (
    id              SERIAL PRIMARY KEY,
    stock_id        INT REFERENCES stocks(id) ON DELETE CASCADE,
    peer_stock_id   INT REFERENCES stocks(id),
    end_date        DATE NOT NULL,
    grossprofit_margin  DECIMAL(12,4),
    netprofit_margin    DECIMAL(12,4),
    roe                 DECIMAL(12,4),
    debt_to_assets      DECIMAL(12,4),
    inv_turn            DECIMAL(12,4),
    ar_turn             DECIMAL(12,4),
    UNIQUE(stock_id, peer_stock_id, end_date)
);

-- ============================================
-- 任务队列（用于数据采集）
-- ============================================

CREATE TABLE collect_tasks (
    id              SERIAL PRIMARY KEY,
    stock_id        INT REFERENCES stocks(id),
    task_type       VARCHAR(50) NOT NULL,              -- income/balance/cashflow/indicator/all
    status          VARCHAR(20) DEFAULT 'pending',      -- pending/running/done/failed
    error_msg       TEXT,
    started_at      TIMESTAMP,
    finished_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 五、规则引擎详解

### 30 条规则分层

| Layer | 名称 | 规则数 | 核心权重 |
|-------|------|--------|----------|
| Layer 0 | 门槛检查 | 2 | 一票否决 |
| Layer 1 | 利润表信号 | 6 | 中 |
| Layer 2 | 现金流量表信号 | 3 | 高 |
| Layer 3 | 资产负债表信号 | 5 | 中 |
| Layer 4 | 交叉验证 | 5 | **最高** |
| Layer 5 | 非财务信号 | 6 | 低 |
| Layer 6 | 行业特有 | 3 | 低 |

### 评分体系

```python
# 基础分计算
基础分 = Σ(WARN数量 × WARN分 + FAIL数量 × FAIL分)

# 组合加分（信号叠加）
- Rule 3.2 FAIL（存货周转↓+毛利率↑）: +10分
- Rule 2.3 FAIL + Rule 4.1 FAIL（大存大贷+CF/利润<1）: +8分
- Rule 1.2 FAIL + Rule 3.1 FAIL: +6分

# 风险等级
| 总分 | 等级 | 颜色 |
|------|------|------|
| 0-10 | 低风险 | 🟢 绿 |
| 11-25 | 中风险 | 🟡 黄 |
| 26-45 | 高风险 | 🟠 橙 |
| 46+ | 极高风险 | 🔴 红 |
| Layer 0 FAIL | 直接排除 | ⚫ 黑 |
```

### 规则实现要点

每条规则的实现遵循以下模式：

```python
class RuleBase:
    """规则基类"""
    code: str           # 规则编号，如 "3.2"
    name: str           # 规则名称
    layer: int          # 所属层级
    weight_warn: int    # WARN 扣分
    weight_fail: int     # FAIL 扣分

    def evaluate(self, context: RuleContext) -> RuleResult:
        """执行规则判定"""
        data = self.fetch_data(context)
        verdict = self.judge(data)
        return RuleResult(
            code=self.code,
            name=self.name,
            verdict=verdict,
            score=self.calc_score(verdict),
            detail=self.format_detail(data, verdict),
            raw_values=data
        )
```

---

## 六、API 设计

### 后端技术栈

- **框架**: FastAPI + Pydantic
- **ORM**: SQLAlchemy 2.0 (async)
- **数据库**: PostgreSQL + asyncpg
- **任务队列**: APScheduler (定时任务) + asyncio (异步采集)
- **缓存**: Redis (可选，用于高频访问)

### API 路由结构

```
/api/v1
├── /stocks
│   ├── GET  /search?q={keyword}          # 股票搜索
│   ├── GET  /{code}                      # 股票基础信息
│   ├── GET  /{code}/profile              # 公司概况（含公告）
│   └── GET  /{code}/main-indicators      # 主要指标
│
├── /finance
│   ├── GET  /{code}/income-statement      # 利润表
│   ├── GET  /{code}/balance-sheet         # 资产负债表
│   ├── GET  /{code}/cash-flow            # 现金流量表
│   ├── GET  /{code}/indicators            # 财务指标
│   └── GET  /{code}/dupont               # 杜邦分析
│
├── /finscan
│   ├── POST /analyze                     # 发起分析（异步）
│   ├── GET  /tasks/{task_id}             # 查询任务状态
│   ├── GET  /reports/{code}/{year}       # 获取报告
│   ├── GET  /reports/{code}/history      # 历史报告
│   ├── POST /batch-scan                   # 批量扫描
│   └── GET  /compare                      # 多股对比
│
├── /watchlist
│   ├── GET    /groups                    # 获取分组
│   ├── POST   /groups                    # 创建分组
│   ├── PUT    /groups/{id}              # 更新分组
│   ├── DELETE /groups/{id}              # 删除分组
│   ├── POST   /groups/{id}/items        # 添加股票
│   ├── DELETE /groups/{id}/items/{stock_id}  # 移除股票
│   └── GET    /groups/{id}/summary       # 分组统计
│
├── /announcements
│   ├── GET  /{code}                      # 公司公告
│   └── GET  /search?q={keyword}         # 公告检索
│
├── /collect
│   ├── POST /trigger                     # 触发采集
│   └── GET  /status/{code}             # 采集状态
│
└── /auth
    ├── POST /login
    ├── POST /register
    └── GET  /me
```

### 响应格式

```json
// 成功响应
{
  "code": 0,
  "data": { ... },
  "message": "success"
}

// 分页响应
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}

// 错误响应
{
  "code": 40401,
  "message": "股票不存在",
  "error": "Stock not found"
}
```

---

## 七、前端架构

### 技术栈

- **框架**: Vue 3 + TypeScript
- **UI 库**: Ant Design Vue
- **图表**: ECharts 5
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **构建**: Vite

### 页面结构

```
/                           # 首页（自选池）
├── /stock/{code}
│   ├── /dashboard          # 核心概览 Dashboard
│   ├── /financials         # 财务报表详解
│   ├── /dupont            # 杜邦分析
│   ├── /cashflow          # 现金流透视
│   ├── /operations        # 经营与业务构成
│   └── /profile           # 公司与股东概况
├── /finscan
│   ├── /                  # 排雷首页
│   └── /report/{code}/{year}  # 排雷报告详情
├── /compare               # 多标对比
├── /announcements         # 公告中心
└── /settings              # 个人设置
```

### 核心组件

| 组件 | 用途 |
|------|------|
| `FinTable` | 财务报表表格，支持多期对比、异常标注、折叠 |
| `DupontTree` | 杜邦分析可视化树 |
| `RiskGauge` | 风险仪表盘（得分+等级） |
| `RulePanel` | 规则详情展开面板 |
| `CashFlowChart` | 现金流结构图 |
| `CompareTable` | 多股对比表格 |
| `StockCard` | 自选股卡片（迷你行情+风险标签） |
| `AnnouncementList` | 公告列表（结构化分类） |

---

## 八、数据采集策略

### 采集层级

```
优先级1（必采）: 三表 + 指标
    ↓ akshare 东财接口
    ↓ 目标：每季度更新

优先级2（建议）: 公告索引
    ↓ akshare 巨潮接口
    ↓ 目标：每日增量

优先级3（可选）: PDF 年报解析
    ↓ 巨潮下载 + pdfplumber
    ↓ 目标：年报披露后48小时内
```

### 定时任务

```python
# APScheduler 配置
SCHEDULE = {
    # 每交易日收盘后更新主要指标
    "daily_indicators": "0 16 * * 1-5",  # 工作日16:00

    # 每季度结束后更新三表
    "quarterly_financials": "0 2 1 */3 *",  # 每季度首日02:00

    # 每日公告增量
    "daily_announcements": "0 22 * * *",    # 每日22:00
}
```

---

## 九、实现计划

### Phase 1: 基础架构 (1周)

- [ ] PostgreSQL 数据库初始化
- [ ] FastAPI 项目搭建
- [ ] SQLAlchemy 模型定义
- [ ] 基础 API 实现（股票搜索、信息查询）
- [ ] 前端项目搭建 + 布局框架

### Phase 2: 财务数据模块 (1周)

- [ ] 三表 API 实现
- [ ] 杜邦分析计算
- [ ] FinTable 组件
- [ ] 公司详情页 Dashboard

### Phase 3: 排雷引擎 (1.5周)

- [ ] 规则引擎框架
- [ ] 30 条规则实现
- [ ] 评分系统
- [ ] 排雷报告页面

### Phase 4: 自选与对比 (1周)

- [ ] 自选分组管理
- [ ] 批量扫描
- [ ] 多股对比
- [ ] 风险可视化

### Phase 5: 完善与优化 (0.5周)

- [ ] 公告中心
- [ ] 数据导出
- [ ] 移动端适配
- [ ] 性能优化

---

## 十、差异化竞争点

| 维度 | 东方财富F10 | Finscan Pro |
|------|-------------|-------------|
| 核心导向 | 行情交易 | 财务分析 |
| 信息组织 | 按报表平铺 | 按分析逻辑分层 |
| 排雷能力 | 无 | 30条规则 + 评分 |
| 对比能力 | 指标少 | 自定义维度 |
| 自定义 | 固定 | 全方位可配 |
| 视觉 | 花哨密集 | 克制降噪 |

---

*本文档为系统设计规范，具体实现请参考代码注释。*
