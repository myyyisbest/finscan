# 上市公司财报智能分析与风险排雷系统 技术开发说明书
## 文档版本：V1.0

## 适用场景：全栈开发落地，可直接用于AI代码生成与工程化实现

---

## 一、项目概述

### 1.1 项目背景

面向财务分析、企业研究、投研人员，打造一款**聚焦基本面、零行情依赖**的上市公司财报分析工具。解决传统财报查阅效率低、风险识别靠经验、多公司对标繁琐的痛点，通过结构化数据沉淀、自动化风险排雷、AI增强解读，大幅提升财报分析效率。

### 1.2 核心目标

1. 构建稳定、低维护成本的财报数据源体系，规避高积分、强反爬的数据源依赖；
2. 实现三大报表标准化存储、多维度对标分析、风险自动排雷三大核心能力；
3. 接入大模型实现财报智能解读，所有结论可溯源，杜绝财务场景幻觉；
4. 采用轻量技术栈，单机可部署，开发周期短，后续可平滑扩展。

### 1.3 功能范围（核心六大模块）

| 模块编号 | 模块名称         | 核心能力                                                                  |
| ---------- | ------------------ | --------------------------------------------------------------------------- |
| M1       | 公司检索与关注池 | 股票代码/名称模糊检索、自定义分组关注、核心指标速览                       |
| M2       | 单公司财报详情   | 三大报表完整展示、财务指标趋势、附注明细查看                              |
| M3       | 多公司对标分析   | 最多8家公司同屏对比，覆盖运营效率、规模绝对值、盈利偿债、结构占比四大维度 |
| M4       | 公告信息中心     | 公告分类检索、财报自动关联、风险公告高亮、原文跳转                        |
| M5       | 财报风险排雷引擎 | 7层30条规则自动筛查、风险等级评定、批量排雷筛选                           |
| M6       | AI智能分析助手   | 财报解读、对标差异分析、公告摘要、自然语言问答                            |

### 1.4 非功能需求

1. **数据准确性**：核心财务数据与官方披露偏差≤0.01%，所有数值保留2位小数，单位统一为人民币元；
2. **性能要求**：单页面加载≤2s，批量排雷100家公司≤30s，接口响应≤500ms；
3. **稳定性**：数据源接口失败自动重试降级，核心功能可用率≥99%；
4. **可扩展性**：规则引擎、AI模型、数据源均采用插件化设计，新增无需重构核心代码；
5. **UI规范**：白蓝商务风格，简洁专业，适配PC端1920*1080标准分辨率，响应式兼容主流屏幕。

---

## 二、总体技术架构

### 2.1 分层架构设计（五层架构）

```
┌───────────────────────────────────────────────────┐
│                  前端交互层（Web端）                │
│  Vue3 + Ant Design Vue + ECharts + 富文本渲染       │
├───────────────────────────────────────────────────┤
│                  业务服务层（后端）                 │
│  FastAPI  RESTful接口 + 规则引擎 + 调度中心         │
├───────────────────────────────────────────────────┤
│                   AI服务层                         │
│  大模型API适配 + RAG检索增强 + 幻觉校验引擎         │
├───────────────────────────────────────────────────┤
│                  数据存储层                         │
│  MariaDB 10.11（主存储+全文索引） + 本地文件缓存    │
├───────────────────────────────────────────────────┤
│                  数据采集层                         │
│  Baostock适配器 + AkShare适配器 + 公告爬虫适配器    │
└───────────────────────────────────────────────────┘
```

### 2.2 技术栈选型

| 层级     | 技术选型                                    | 选型说明                                                              |
| ---------- | --------------------------------------------- | ----------------------------------------------------------------------- |
| 后端框架 | Python 3.10 + FastAPI                       | 与数据采集、Pandas处理技术栈统一，异步高性能，接口文档自动生成        |
| 数据库   | MariaDB 10.11 LTS                           | 兼容MySQL语法，轻量高性能，自带全文索引支持公告检索，单机承载全量数据 |
| 前端框架 | Vue 3.4 + Vite + Ant Design Vue 4.x         | 组件丰富，商务风格适配性强，开发效率高                                |
| 图表库   | ECharts 5.x                                 | 覆盖柱状图、折线图、雷达图、对比图等所有财务可视化场景                |
| 数据采集 | Baostock 最新版 + AkShare 最新版 + Requests | 主数据稳定无反爬，附注按需补充，零成本                                |
| 任务调度 | APScheduler                                 | 轻量内置调度器，支持定时增量同步，无需额外部署中间件                  |
| AI接入   | 统一大模型适配层                            | 兼容通义千问、DeepSeek、本地开源模型，可插拔切换                      |
| 部署方式 | Docker + Nginx                              | 一键部署，反向代理，静态资源分离                                      |

### 2.3 核心设计原则

1. **数据源分层解耦**：所有数据源通过适配器封装，上层业务不感知底层数据源差异，更换数据源仅需修改适配器；
2. **缓存优先**：所有采集到的数据永久入库缓存，杜绝重复请求，既规避反爬也提升响应速度；
3. **规则与代码分离**：排雷规则配置化存储，新增/修改规则无需改代码，重启即可生效；
4. **AI边界严格**：AI仅做数据解读与文本整理，所有数值结论必须来自数据库，禁止生成虚构数据；
5. **渐进式开发**：按MVP→完善版→增强版三阶段落地，每个阶段均可独立运行交付。

---

## 三、数据库详细设计（MariaDB）

### 3.1 命名规范

- 表名：小写蛇形命名，前缀区分域，如 `stock_` 基础域、`fin_` 财务域、`ann_` 公告域、`risk_` 排雷域；
- 字段名：小写蛇形，金额类字段统一用 `DECIMAL(20,4)`，日期用 `DATE`，布尔值用 `TINYINT(1)`；
- 主键：统一自增 `id` 作为物理主键，业务唯一键建唯一索引。

### 3.2 核心表结构（含完整建表SQL）

#### 3.2.1 公司基础信息域

```sql
-- 股票基础档案表
CREATE TABLE stock_basic (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码 格式：600519.SH',
    stock_name VARCHAR(50) NOT NULL COMMENT '股票简称',
    full_name VARCHAR(100) DEFAULT NULL COMMENT '公司全称',
    industry VARCHAR(50) DEFAULT NULL COMMENT '申万一级行业',
    market VARCHAR(20) DEFAULT NULL COMMENT '市场板块：主板/创业板/科创板/北交所',
    list_date DATE DEFAULT NULL COMMENT '上市日期',
    is_st TINYINT(1) DEFAULT 0 COMMENT '是否ST 0否1是',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_stock_code (stock_code),
    INDEX idx_name (stock_name),
    INDEX idx_industry (industry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基础信息表';

-- 用户关注池表
CREATE TABLE stock_watchlist (
    id INT PRIMARY KEY AUTO_INCREMENT,
    group_name VARCHAR(50) NOT NULL DEFAULT '默认分组' COMMENT '分组名称',
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    add_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    remark VARCHAR(200) DEFAULT NULL COMMENT '备注',
    UNIQUE KEY uk_group_stock (group_name, stock_code),
    INDEX idx_group (group_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关注池表';
```

#### 3.2.2 财务核心数据域（Baostock主数据）

```sql
-- 资产负债表
CREATE TABLE fin_balance_sheet (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL COMMENT '报告期 如2024-12-31',
    report_type VARCHAR(10) NOT NULL COMMENT '报告类型：一季报/中报/三季报/年报',
    -- 核心资产科目
    total_assets DECIMAL(20,4) DEFAULT NULL COMMENT '总资产',
    total_current_assets DECIMAL(20,4) DEFAULT NULL COMMENT '流动资产合计',
    monetary_funds DECIMAL(20,4) DEFAULT NULL COMMENT '货币资金',
    accounts_receivable DECIMAL(20,4) DEFAULT NULL COMMENT '应收账款',
    inventory DECIMAL(20,4) DEFAULT NULL COMMENT '存货',
    total_noncurrent_assets DECIMAL(20,4) DEFAULT NULL COMMENT '非流动资产合计',
    fixed_assets DECIMAL(20,4) DEFAULT NULL COMMENT '固定资产',
    construction_in_progress DECIMAL(20,4) DEFAULT NULL COMMENT '在建工程',
    intangible_assets DECIMAL(20,4) DEFAULT NULL COMMENT '无形资产',
    goodwill DECIMAL(20,4) DEFAULT NULL COMMENT '商誉',
    long_deferred_expenses DECIMAL(20,4) DEFAULT NULL COMMENT '长期待摊费用',
    -- 核心负债科目
    total_liabilities DECIMAL(20,4) DEFAULT NULL COMMENT '总负债',
    total_current_liabilities DECIMAL(20,4) DEFAULT NULL COMMENT '流动负债合计',
    short_term_borrowings DECIMAL(20,4) DEFAULT NULL COMMENT '短期借款',
    accounts_payable DECIMAL(20,4) DEFAULT NULL COMMENT '应付账款',
    total_noncurrent_liabilities DECIMAL(20,4) DEFAULT NULL COMMENT '非流动负债合计',
    long_term_borrowings DECIMAL(20,4) DEFAULT NULL COMMENT '长期借款',
    bonds_payable DECIMAL(20,4) DEFAULT NULL COMMENT '应付债券',
    -- 所有者权益
    total_equity DECIMAL(20,4) DEFAULT NULL COMMENT '股东权益合计',
    share_capital DECIMAL(20,4) DEFAULT NULL COMMENT '股本',
    capital_reserve DECIMAL(20,4) DEFAULT NULL COMMENT '资本公积',
    retained_profits DECIMAL(20,4) DEFAULT NULL COMMENT '未分配利润',
    other_receivables DECIMAL(20,4) DEFAULT NULL COMMENT '其他应收款',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_report (stock_code, report_date),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资产负债表';

-- 利润表
CREATE TABLE fin_income_statement (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    report_type VARCHAR(10) NOT NULL,
    total_revenue DECIMAL(20,4) DEFAULT NULL COMMENT '营业总收入',
    operating_cost DECIMAL(20,4) DEFAULT NULL COMMENT '营业成本',
    gross_profit DECIMAL(20,4) DEFAULT NULL COMMENT '毛利润',
    gross_margin DECIMAL(10,4) DEFAULT NULL COMMENT '毛利率%',
    selling_expenses DECIMAL(20,4) DEFAULT NULL COMMENT '销售费用',
    admin_expenses DECIMAL(20,4) DEFAULT NULL COMMENT '管理费用',
    rd_expenses DECIMAL(20,4) DEFAULT NULL COMMENT '研发费用',
    financial_expenses DECIMAL(20,4) DEFAULT NULL COMMENT '财务费用',
    operating_profit DECIMAL(20,4) DEFAULT NULL COMMENT '营业利润',
    total_profit DECIMAL(20,4) DEFAULT NULL COMMENT '利润总额',
    net_profit DECIMAL(20,4) DEFAULT NULL COMMENT '净利润',
    net_profit_parent DECIMAL(20,4) DEFAULT NULL COMMENT '归母净利润',
    net_profit_deduct DECIMAL(20,4) DEFAULT NULL COMMENT '扣非净利润',
    asset_impairment_loss DECIMAL(20,4) DEFAULT NULL COMMENT '资产减值损失',
    other_income DECIMAL(20,4) DEFAULT NULL COMMENT '其他收益',
    investment_income DECIMAL(20,4) DEFAULT NULL COMMENT '投资收益',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_report (stock_code, report_date),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='利润表';

-- 现金流量表
CREATE TABLE fin_cash_flow (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    report_type VARCHAR(10) NOT NULL,
    operating_cash_inflow DECIMAL(20,4) DEFAULT NULL COMMENT '经营活动现金流入小计',
    operating_cash_outflow DECIMAL(20,4) DEFAULT NULL COMMENT '经营活动现金流出小计',
    operating_cash_net DECIMAL(20,4) DEFAULT NULL COMMENT '经营活动现金流量净额',
    sales_cash_received DECIMAL(20,4) DEFAULT NULL COMMENT '销售商品收到的现金',
    investing_cash_net DECIMAL(20,4) DEFAULT NULL COMMENT '投资活动现金流量净额',
    financing_cash_net DECIMAL(20,4) DEFAULT NULL COMMENT '筹资活动现金流量净额',
    capital_expenditure DECIMAL(20,4) DEFAULT NULL COMMENT '资本开支',
    free_cash_flow DECIMAL(20,4) DEFAULT NULL COMMENT '自由现金流',
    cash_ending_balance DECIMAL(20,4) DEFAULT NULL COMMENT '期末现金及现金等价物余额',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_report (stock_code, report_date),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='现金流量表';

-- 衍生财务指标表（预计算，避免重复计算）
CREATE TABLE fin_indicators (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    report_type VARCHAR(10) NOT NULL,
    -- 盈利能力
    roe DECIMAL(10,4) DEFAULT NULL COMMENT '净资产收益率%',
    roa DECIMAL(10,4) DEFAULT NULL COMMENT '总资产收益率%',
    net_margin DECIMAL(10,4) DEFAULT NULL COMMENT '净利率%',
    -- 偿债能力
    debt_to_assets DECIMAL(10,4) DEFAULT NULL COMMENT '资产负债率%',
    current_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '流动比率',
    quick_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '速动比率',
    -- 营运能力
    ar_turnover DECIMAL(10,4) DEFAULT NULL COMMENT '应收账款周转率(次)',
    inventory_turnover DECIMAL(10,4) DEFAULT NULL COMMENT '存货周转率(次)',
    total_asset_turnover DECIMAL(10,4) DEFAULT NULL COMMENT '总资产周转率(次)',
    operating_cycle DECIMAL(10,2) DEFAULT NULL COMMENT '营业周期(天)',
    ap_turnover DECIMAL(10,4) DEFAULT NULL COMMENT '应付账款周转率(次)',
    -- 成长能力
    revenue_yoy DECIMAL(10,4) DEFAULT NULL COMMENT '营收同比增速%',
    net_profit_yoy DECIMAL(10,4) DEFAULT NULL COMMENT '净利润同比增速%',
    -- 现金流质量
    cf_to_net_profit DECIMAL(10,4) DEFAULT NULL COMMENT '经营现金流/净利润',
    sales_cash_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '销售收现比',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_report (stock_code, report_date),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财务指标表';
```

#### 3.2.3 财务附注数据域（AkShare按需缓存）

```sql
-- 主营业务拆分明细
CREATE TABLE note_main_business (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    biz_type VARCHAR(20) NOT NULL COMMENT '拆分维度：产品/行业/地区',
    biz_name VARCHAR(100) NOT NULL COMMENT '业务名称',
    revenue DECIMAL(20,4) DEFAULT NULL COMMENT '营业收入',
    cost DECIMAL(20,4) DEFAULT NULL COMMENT '营业成本',
    gross_profit DECIMAL(20,4) DEFAULT NULL COMMENT '毛利',
    gross_margin DECIMAL(10,4) DEFAULT NULL COMMENT '毛利率%',
    revenue_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '收入占比%',
    fetch_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_report_biz (stock_code, report_date, biz_type, biz_name),
    INDEX idx_stock_report (stock_code, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='主营业务拆分附注';

-- 应收账款账龄明细
CREATE TABLE note_receivable_age (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    age_range VARCHAR(30) NOT NULL COMMENT '账龄区间 如1年以内',
    balance DECIMAL(20,4) DEFAULT NULL COMMENT '账面余额',
    provision DECIMAL(20,4) DEFAULT NULL COMMENT '坏账准备',
    provision_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '计提比例%',
    fetch_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_report_age (stock_code, report_date, age_range),
    INDEX idx_stock_report (stock_code, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应收账款账龄附注';

-- 前五大客户/供应商
CREATE TABLE note_top_counterparties (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    counterpart_type VARCHAR(10) NOT NULL COMMENT '客户/供应商',
    rank TINYINT NOT NULL COMMENT '排名1-5',
    counterpart_name VARCHAR(100) DEFAULT NULL COMMENT '对方名称',
    amount DECIMAL(20,4) DEFAULT NULL COMMENT '交易金额',
    ratio DECIMAL(10,4) DEFAULT NULL COMMENT '占比%',
    fetch_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_report_type_rank (stock_code, report_date, counterpart_type, rank),
    INDEX idx_stock_report (stock_code, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='前五大客户供应商附注';
```

#### 3.2.4 公告信息域

```sql
CREATE TABLE ann_announcement (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    ann_title VARCHAR(200) NOT NULL COMMENT '公告标题',
    ann_type VARCHAR(30) NOT NULL COMMENT '公告类型：定期报告/业绩预告/并购重组/监管问询/分红派息/其他',
    publish_date DATE NOT NULL COMMENT '发布日期',
    pdf_url VARCHAR(300) DEFAULT NULL COMMENT '官方PDF链接',
    content_summary TEXT DEFAULT NULL COMMENT '公告摘要文本',
    related_report_date DATE DEFAULT NULL COMMENT '关联财报期',
    is_risk TINYINT(1) DEFAULT 0 COMMENT '是否风险公告 0否1是',
    source VARCHAR(20) DEFAULT '巨潮' COMMENT '数据来源',
    fetch_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_pdf (stock_code, pdf_url(200)),
    INDEX idx_stock_publish (stock_code, publish_date),
    INDEX idx_type (ann_type),
    FULLTEXT KEY ft_title_content (ann_title, content_summary)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='上市公司公告表';
```

#### 3.2.5 风险排雷域

```sql
-- 排雷规则配置表
CREATE TABLE risk_rules (
    id INT PRIMARY KEY AUTO_INCREMENT,
    rule_code VARCHAR(10) NOT NULL COMMENT '规则编号 如1.1',
    rule_name VARCHAR(100) NOT NULL COMMENT '规则名称',
    rule_layer TINYINT NOT NULL COMMENT '所属层级0-6',
    rule_desc TEXT DEFAULT NULL COMMENT '规则说明',
    warn_threshold TEXT DEFAULT NULL COMMENT '预警阈值 JSON格式',
    fail_threshold TEXT DEFAULT NULL COMMENT '失败阈值 JSON格式',
    warn_score DECIMAL(3,1) NOT NULL DEFAULT 2 COMMENT '预警得分',
    fail_score DECIMAL(3,1) NOT NULL DEFAULT 5 COMMENT '失败得分',
    data_source VARCHAR(20) NOT NULL COMMENT '数据源：baostock/akshare/announcement',
    is_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    UNIQUE KEY uk_rule_code (rule_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排雷规则配置表';

-- 排雷结果主表
CREATE TABLE risk_report (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    total_score DECIMAL(5,1) NOT NULL COMMENT '总风险得分',
    risk_level VARCHAR(10) NOT NULL COMMENT '风险等级：低/中/高/极高/直接排除',
    rule_total INT NOT NULL COMMENT '总规则数',
    rule_participated INT NOT NULL COMMENT '参评规则数',
    data_completeness DECIMAL(5,2) NOT NULL COMMENT '数据完整度%',
    calc_time DATETIME NOT NULL,
    UNIQUE KEY uk_stock_report (stock_code, report_date),
    INDEX idx_risk_level (risk_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排雷报告主表';

-- 单条规则判定明细表
CREATE TABLE risk_rule_result (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    rule_code VARCHAR(10) NOT NULL,
    result VARCHAR(10) NOT NULL COMMENT 'PASS/WARN/FAIL/SKIP',
    score DECIMAL(3,1) NOT NULL DEFAULT 0 COMMENT '本条得分',
    evidence TEXT DEFAULT NULL COMMENT '判定证据 原始数值',
    calc_time DATETIME NOT NULL,
    UNIQUE KEY uk_stock_rule (stock_code, report_date, rule_code),
    INDEX idx_stock_report (stock_code, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='规则判定明细表';
```

### 3.3 索引设计原则

1. 所有业务唯一键建立唯一索引，保证数据幂等；
2. 高频查询字段（stock_code、report_date）建立联合索引；
3. 公告表标题与摘要建立全文索引，支持关键词模糊检索；
4. 大表避免过多索引，控制单表索引数量≤6个。

---

## 四、数据采集层详细设计

### 4.1 整体采集策略

采用「**批量预同步 + 按需补全**」双模式，核心数据提前入库，低频附注按需触发缓存，最大化稳定性、最小化反爬风险。

### 4.2 Baostock 采集适配器（核心主数据）

#### 4.2.1 采集范围

- 全A股上市公司基础信息；
- 近3年所有定期报告：资产负债表、利润表、现金流量表；
- 配套衍生财务指标。

#### 4.2.2 采集调度

- **全量初始化**：项目上线前一次性执行，遍历全A股近3年财报，串行执行；
- **每日增量同步**：每日凌晨2:00执行，检查前一日新披露的财报，仅增量插入更新；
- **季度全量校验**：财报季结束后执行全量校验，补全缺失数据。

#### 4.2.3 字段映射规则

Baostock返回字段与数据库表字段一一映射，统一单位为元，保留4位小数。
示例映射关系：

| Baostock字段 | 数据库字段        | 说明         |
| -------------- | ------------------- | -------------- |
| totalAssets  | total_assets      | 总资产       |
| netProfit    | net_profit_parent | 归母净利润   |
| ROE          | roe               | 净资产收益率 |

#### 4.2.4 数据清洗与校验

1. **空值处理**：空值统一存为NULL，不填0，避免指标计算错误；
2. **单位统一**：所有金额统一转换为元，剔除「亿、万」单位后缀；
3. **勾稽校验**：

   - 资产负债表：总资产 ≈ 总负债 + 股东权益，偏差超过0.1%标记异常；
   - 利润表：毛利润 = 营业收入 - 营业成本，自动计算校验；
4. **去重幂等**：按 `stock_code + report_date` 唯一键判断，存在则更新，不存在则插入。

#### 4.2.5 异常处理

- 接口请求失败自动重试3次，间隔5秒；
- 连续失败记录错误日志，跳过当前股票，继续执行后续标的；
- 每日同步完成后生成采集报告，统计成功/失败数量。

### 4.3 AkShare 附注采集适配器（按需缓存）

#### 4.3.1 采集范围

- 主营业务拆分（产品/行业/地区）；
- 应收账款账龄明细；
- 前五大客户/供应商占比；
- 研发资本化明细。

#### 4.3.2 触发机制

- **懒加载触发**：用户首次进入单公司「附注明细」页或触发排雷计算时，才发起接口请求；
- **永久缓存**：拉取成功后立即写入数据库，后续所有请求直接读库，不再调用接口。

#### 4.3.3 反爬防护机制（强制实现）

1. **全局单线程串行**：所有AkShare请求全局加锁，同一时间仅一个请求发出；
2. **随机长延时**：每次调用前随机休眠 `2.5 ~ 4.5秒`，禁止固定间隔；
3. **请求头伪装**：底层requests携带随机UA、完整Referer、Accept头；
4. **失败退避**：请求失败后，指数退避重试（10s→30s→60s），最多3次；
5. **熔断机制**：连续10次请求失败，自动熔断1小时，期间所有附注请求直接返回「数据加载中」；
6. **本地IP优先**：禁止云服务器高并发调用，仅本地部署或低频率调用。

#### 4.3.4 降级方案

AkShare接口不可用时，前端展示「暂未收录该附注明细，可查看官方年报PDF」，并提供巨潮原文跳转链接，不阻塞核心功能。

### 4.4 公告采集适配器

#### 4.4.1 数据源

- 主源：巨潮资讯公开公告接口（`hisAnnouncement/query`）；
- 备源：AkShare公告接口。

#### 4.4.2 采集策略

- **每日增量**：每日凌晨3:00同步前一交易日全部A股新公告；
- **历史按需**：单公司历史公告仅在用户进入公告页时，按需拉取近2年数据并缓存。

#### 4.4.3 公告分类逻辑

基于标题关键词匹配自动分类：

- 定期报告：包含「年度报告、半年度报告、第一季度报告、第三季度报告」；
- 业绩预告：包含「业绩预告、业绩快报」；
- 并购重组：包含「收购、重组、并购、重大资产」；
- 监管问询：包含「问询函、监管函、警示函、立案调查」；
- 分红派息：包含「分红、派息、转增、权益分派」；
- 其他：未命中以上关键词。

#### 4.4.4 风险公告识别

标题包含「立案调查、行政处罚、警示函、监管函、问询函、ST、退市」等关键词，自动标记为风险公告（is_risk=1）。

---

## 五、核心业务模块详细设计

### 5.1 M1 公司检索与关注池模块

#### 5.1.1 功能流程

1. 用户在顶部搜索框输入股票代码/名称，前端实时调用检索接口，返回联想列表；
2. 支持按行业、市场板块、ST状态筛选；
3. 选中股票可加入指定关注分组，支持新建分组；
4. 关注池页面按分组展示股票列表，同步展示核心指标（最新年报营收、净利润、ROE、风险等级）。

#### 5.1.2 核心后端接口

| 接口路径                 | 方法   | 功能说明                     |
| -------------------------- | -------- | ------------------------------ |
| /api/stock/search        | GET    | 关键词模糊检索股票，支持分页 |
| /api/stock/basic/{code}  | GET    | 获取单只股票基础信息         |
| /api/watchlist/list      | GET    | 获取我的关注池分组与股票列表 |
| /api/watchlist/add       | POST   | 添加股票到关注池             |
| /api/watchlist/remove    | DELETE | 从关注池移除股票             |
| /api/watchlist/group/add | POST   | 新建关注分组                 |

#### 5.1.3 前端页面

- 顶部全局搜索栏，支持输入即时联想；
- 左侧分组导航，右侧股票列表，卡片式布局展示核心指标与风险等级色标；
- 支持批量添加、批量移除、分组移动。

### 5.2 M2 单公司财报详情模块

#### 5.2.1 页面结构（Tab页签式）

1. **财务总览**：核心指标卡片、近3年趋势折线图、核心科目变化摘要；
2. **三大报表**：资产负债表、利润表、现金流量表切换展示，支持年度/季度切换，同比数据自动标注；
3. **财务指标**：四大类指标（盈利、偿债、营运、成长）表格+趋势图；
4. **附注明细**：主营业务拆分、账龄明细、前五大客户，按需加载；
5. **风险排雷**：独立Tab，详见M5模块；
6. **公告列表**：该公司全部公告，按时间倒序。

#### 5.2.2 核心交互

- 所有金额支持「元/万元/亿元」一键切换单位；
- 表格支持列排序、关键科目高亮；
- 同比增减自动标红（增长）标绿（下降）。

### 5.3 M3 多公司对标分析模块

#### 5.3.1 核心能力

支持最多8家公司同时对比，四大对比维度：

1. **运营效率对比（重点）** ：应收账款周转率、存货周转率、总资产周转率、应付账款周转率、营业周期；

   - 展示形式：柱状对比图 + 多期趋势折线图；
   - 自动标注行业中位值参考线。
2. **规模绝对值对比**：总资产、总负债、净资产、营业总收入、营业成本、归母净利润、经营现金流净额；

   - 支持绝对金额/同比增速两种视图切换。
3. **盈利与偿债对比**：毛利率、净利率、ROE、资产负债率、流动比率、速动比率；
4. **结构占比对比**：资产结构、成本费用结构占比，环形图+表格联动。

#### 5.3.2 业务流程

1. 用户从关注池勾选或搜索添加对标公司；
2. 选择对比报告期（默认最新年报）；
3. 切换对比维度，自动生成图表与对比表格；
4. 支持导出对比结果Excel/PDF。

#### 5.3.3 核心后端接口

| 接口路径                     | 方法 | 功能说明                     |
| ------------------------------ | ------ | ------------------------------ |
| /api/compare/indicators      | POST | 批量获取多家公司指定指标     |
| /api/compare/trend           | POST | 批量获取多家公司多年趋势数据 |
| /api/compare/industry/median | GET  | 获取指定行业的指标中位值     |

### 5.4 M4 公告信息中心模块

#### 5.4.1 功能点

1. 多维度筛选：公告类型、发布时间、风险标记、关键词全文检索；
2. 单公司时间线展示 + 全市场公告列表两种视图；
3. 公告详情页展示摘要、核心关键词高亮、关联财报期跳转、官方PDF原文跳转；
4. 风险公告红色标记，置顶优先展示。

#### 5.4.2 检索实现

基于MariaDB全文索引实现关键词检索，支持标题+摘要联合搜索，结果按发布时间倒序。

---

## 六、财报风险排雷引擎详细设计

### 6.1 规则体系（7层30条，落地优先级分级）

#### 6.1.1 第一优先级：Baostock预计算（22条，MVP上线）

| 层级   | 规则编号 | 规则名称              | 判定逻辑                                              | 阈值         |
| -------- | ---------- | ----------------------- | ------------------------------------------------------- | -------------- |
| Layer0 | 0.2      | 年报按时披露          | 超4月30日未披露直接FAIL                               | -            |
| Layer1 | 1.1      | 毛利率异常波动        | 同比波动>5pp WARN，>10pp且高于同行FAIL                | 5pp / 10pp   |
| Layer1 | 1.2      | 毛利升+应收升+应付降  | 三项同时满足FAIL                                      | 三项同时成立 |
| Layer1 | 1.4      | 其他业务收入占比突增  | 占比>5%且同比+3pp WARN，>15% FAIL                     | 5% / 15%     |
| Layer1 | 1.5      | 费用率异常下降        | 低于3年均值3pp WARN，5pp FAIL                         | 3pp / 5pp    |
| Layer1 | 1.6      | 资产减值损失暴增      | 同比>50% WARN，>100% FAIL                             | 50% / 100%   |
| Layer2 | 2.1      | 经营CF好+投资CF持续负 | 投资CF>经营CF80% WARN，连续3年超FAIL                  | 80% / 3年    |
| Layer2 | 2.2      | 经营CF持续为负        | 近5年2年负WARN，连续3年负FAIL                         | 2年 / 3年    |
| Layer2 | 2.3      | 存贷双高              | 货币资金>有息负债但财务费用率偏高+2pp WARN，+4pp FAIL | 2pp / 4pp    |
| Layer3 | 3.1      | 应收增速>收入增速     | 1.5倍WARN，2倍FAIL                                    | 1.5x / 2x    |
| Layer3 | 3.2      | 存货周转降+毛利率升   | 周转率降>10%且毛利升WARN，强烈背离FAIL                | 10%下降      |
| Layer3 | 3.3      | 在建工程不转固        | 在建工程增>30%无固定资产增加WARN，持续3年FAIL         | 30% / 3年    |
| Layer3 | 3.4      | 长期待摊费用大增      | 同比>50% WARN，>100% FAIL                             | 50% / 100%   |
| Layer4 | 4.1      | 经营CF/净利润<1       | 近5年2年<1 WARN，连续3年FAIL                          | 2年 / 3年    |
| Layer4 | 4.2      | 销售收现/营收<1       | <0.9 WARN，<0.8持续2年FAIL                            | 0.9 / 0.8    |
| Layer4 | 4.3      | 利润膨胀资产膨胀      | 资产增速>营收增速2倍WARN，3倍FAIL                     | 2x / 3x      |
| Layer4 | 4.4      | 核心利润与净利润背离  | 偏差>20% WARN，>40% FAIL                              | 20% / 40%    |
| Layer4 | 4.5      | 净利润增+FCF持续负    | 2年负WARN，3年负FAIL                                  | 2年 / 3年    |
| Layer5 | 5.7      | 商誉占比过高          | 商誉/净资产>20% WARN，>40% FAIL                       | 20% / 40%    |
| Layer5 | 5.8      | 其他应收款异常        | 占总资产>3%或同比>30% WARN，>5%或>50% FAIL            | 3% / 5%      |
| Layer6 | 6.1      | 农林渔牧行业          | 行业匹配自动WARN                                      | -            |

#### 6.1.2 第二优先级：AkShare附注（6条，附注模块上线后）

1.3运费增速、3.5坏账计提比例、5.5客户集中度、5.3财务总监更换、5.2大股东减持、6.2研发资本化比例

#### 6.1.3 第三优先级：公告数据（2条，公告模块上线后）

0.1审计意见、5.1更换审计机构、5.4独董辞职、5.9监管处罚

### 6.2 评分与分级体系

#### 6.2.1 基础权重

| 层级               | WARN单条得分 | FAIL单条得分 |
| -------------------- | -------------- | -------------- |
| Layer 0            | -            | 直接排除     |
| Layer 1 利润表     | 2分          | 5分          |
| Layer 2 现金流     | 3分          | 6分          |
| Layer 3 资产负债表 | 2分          | 5分          |
| Layer 4 交叉验证   | 3分          | 7分          |
| Layer 5 非财务     | 1分          | 3分          |
| Layer 6 行业       | 1分          | 3分          |

#### 6.2.2 组合加分项

- 规则3.2 FAIL：+10分
- 规则2.3 FAIL + 4.1 FAIL：+8分
- 规则1.2 FAIL + 3.1 FAIL：+6分

#### 6.2.3 风险等级

| 总得分       | 风险等级 | 颜色标识       |
| -------------- | ---------- | ---------------- |
| 0-10         | 低风险   | 绿色 #52c41a   |
| 11-25        | 中风险   | 黄色 #faad14   |
| 26-45        | 高风险   | 橙色 #fa8c16   |
| ≥46         | 极高风险 | 红色 #f5222d   |
| Layer0未通过 | 直接排除 | 深红色 #cf1322 |

### 6.3 规则引擎实现

#### 6.3.1 执行流程

1. **数据准备**：从财务表中提取对应公司、对应期间的所有科目与指标数据；
2. **规则遍历**：按层级依次执行所有启用的规则，逐条判定结果（PASS/WARN/FAIL/SKIP）；
3. **得分计算**：根据判定结果累加得分，叠加组合加分；
4. **等级评定**：根据总得分匹配风险等级；
5. **结果持久化**：写入risk_report与risk_rule_result表；
6. **缓存更新**：更新关注池列表的风险等级展示。

#### 6.3.2 计算调度

- **预计算**：每日财报增量同步完成后，自动批量计算所有新增报告期的排雷结果；
- **实时补算**：用户查看排雷报告时，检查是否有未计算的附注/公告类规则，按需补算；
- **重算触发**：规则配置修改、财报数据修正后，触发对应数据的重算。

### 6.4 批量排雷功能

- 支持对关注池、指定行业、自定义股票列表批量执行排雷；
- 结果表格化展示，支持按风险等级、规则维度筛选；
- 支持一键导出Excel结果。

---

## 七、AI智能分析模块详细设计

### 7.1 核心设计原则

**规则引擎做判定，AI做解读**：AI绝对不修改规则结果、不虚构财务数据，所有输出严格基于数据库已有的真实数据，所有结论可溯源。

### 7.2 技术架构：本地数据RAG（检索增强生成）

```
用户提问 → 意图解析 → 数据检索（从MariaDB提取对应财报/公告/排雷数据）
→ 上下文拼装（固定Prompt + 真实数据 + 输出约束）
→ 大模型生成 → 幻觉校验（检查数值是否与源数据一致）
→ 结果返回 + 溯源标注
```

### 7.3 四大核心AI功能

#### 7.3.1 单公司财报智能解读

- **触发方式**：单公司财报页点击「AI解读」按钮
- **输入数据**：公司近3年核心财务指标、三大报表关键科目变化、同比增速、排雷风险点
- **输出结构**：

  1. 整体经营概况（100字以内）
  2. 核心变化点拆解（3-5条，每条绑定具体数值与期间）
  3. 财务风险提示（基于排雷结果，说明风险点与影响）
  4. 现金流质量评价
- **约束要求**：所有数字必须来自数据库，禁止使用「大幅增长」等模糊表述，必须带具体数值与同比。

#### 7.3.2 对标差异智能分析

- **触发方式**：对标分析页点击「AI解读差异」
- **输入数据**：多家公司的指标对比数据、行业中位值
- **输出内容**：各家公司核心优劣势总结、运营效率差异分析、标的行业定位评价

#### 7.3.3 公告一键摘要

- **触发方式**：公告详情页点击「AI摘要」
- **输入数据**：公告全文文本
- **输出内容**：3句话核心摘要 + 事件定性（利好/利空/中性） + 潜在财务影响提示

#### 7.3.4 自然语言问答助手

- **触发方式**：全局对话入口
- **能力范围**：仅回答数据库内的财报数据相关问题，拒绝回答股价预测、投资建议、非数据类问题
- **示例**：「长安汽车近3年应收账款周转率变化」「对比茅台和五粮液的毛利率差异」
- **实现逻辑**：解析用户问题 → 生成SQL查询条件 → 执行查询获取数据 → 大模型组织语言 → 校验数值 → 返回结果

### 7.4 幻觉防控机制（强制实现）

1. **输入边界限制**：Prompt中明确限定「只能使用提供的数据回答，禁止编造数据，数据不足时说明无法回答」；
2. **输出数值校验**：对生成结果中的所有数字做正则提取，与源数据比对，偏差超过0.1%直接拦截；
3. **强制溯源标注**：每个结论后标注「数据来源：2024年年报 利润表」，点击可跳转对应位置；
4. **禁用输出清单**：禁止生成投资建议、买卖指导、股价预测、避税方案等内容；
5. **兜底回复**：超出能力范围的问题统一返回「该问题超出当前数据范围，建议查阅官方公告原文」。

### 7.5 模型适配层

- 封装统一大模型客户端，支持切换通义千问、DeepSeek、本地开源模型；
- 支持配置模型参数（temperature=0.1，极低随机性，保证输出稳定）；
- 记录所有AI调用日志，包含输入、输出、耗时、校验结果，便于排查。

---

## 八、后端服务设计

### 8.1 接口规范

- 统一RESTful风格，路径前缀 `/api`；
- 统一返回格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": 1718888888
}
```

- 错误码规范：0成功，1001参数错误，2001数据不存在，3001权限错误，5000服务器内部错误。

### 8.2 分层架构

```
Controller层 → Service层 → Data Access层（SQLAlchemy）→ 数据库
              ↓
         适配器层（Baostock/AkShare/公告）→ 外部数据源
              ↓
         规则引擎 + AI服务
```

### 8.3 调度中心

- 使用APScheduler内置调度器；
- 定时任务列表：

  1. 每日02:00：Baostock财报增量同步
  2. 每日03:00：公告增量同步
  3. 每日04:00：财务指标预计算 + 排雷结果预计算
  4. 每周一01:00：全量数据完整性校验

### 8.4 日志与监控

- 接口访问日志、错误日志、采集日志分级存储；
- 关键操作（数据修改、规则变更）留痕审计；
- 每日生成运行日报，统计数据量、接口成功率、AI调用量。

---

## 九、前端系统设计

### 9.1 技术栈

- 构建工具：Vite 5
- 框架：Vue 3 + Composition API + Pinia状态管理
- UI组件库：Ant Design Vue 4.x
- 图表库：ECharts 5.x
- 路由：Vue Router 4

### 9.2 UI设计规范

- **主色调**：商务蓝 #165DFF，辅助色：浅蓝 #E8F3FF
- **中性色**：以白、浅灰为主，页面背景 #F5F7FA
- **风格**：扁平化、卡片式布局，大留白，无多余装饰，突出数据
- **字体**：默认系统无衬线字体，数字使用等宽字体

### 9.3 页面路由结构

```
/ 首页（快速检索 + 关注池概览 + 风险提示）
/stock/:code 单公司详情页（多Tab）
/compare 对标分析页
/announcement 公告中心
/risk 批量排雷中心
/help 使用帮助与规则说明
```

### 9.4 核心组件

- 全局搜索组件
- 财务指标卡片组件
- 通用对比柱状图组件
- 趋势折线图组件
- 财报表格组件（支持单位切换、同比高亮）
- 风险等级标签组件

---

## 十、部署与运维方案

### 10.1 部署架构（单机轻量部署）

- 服务器配置：2核4G云服务器即可承载全量数据与日常访问；
- 部署方式：Docker Compose 一键编排，包含三个容器：

  1. MariaDB 容器（数据持久化挂载宿主机目录）
  2. FastAPI 后端服务容器
  3. Nginx 容器（静态资源 + 反向代理）

### 10.2 数据备份

- 每日凌晨自动全量备份MariaDB，保留30天备份；
- 备份文件自动压缩，支持异地存储。

### 10.3 扩容方案

- 初期单机部署即可满足需求；
- 后续用户量增长，可拆分数据库与应用服务，增加缓存层Redis。

---

## 十一、开发排期与里程碑

| 阶段               | 周期 | 核心交付物                                                                                                                                                       | 验收标准                           |
| -------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------ |
| 阶段一：MVP基础版  | 2周  | 1. MariaDB库表搭建完成<br />2. Baostock近3年财报全量入库<br />3. 公司检索、关注池、单公司财报详情<br />4. 基础对标分析（运营指标+绝对值对比）<br />5. 前端核心页面               | 可正常查看公司财报，完成多公司对标 |
| 阶段二：功能完善版 | 2周  | 1. AkShare附注按需采集与缓存<br />2. 公告模块上线（增量同步、分类检索）<br />3. 22条核心排雷规则上线，单公司排雷报告<br />4. 批量排雷筛选器<br />5. 三大报表完整展示、指标趋势图 | 排雷功能可用，公告可检索           |
| 阶段三：AI增强版   | 2周  | 1. 大模型适配层接入<br />2. 财报AI解读、公告摘要、对标分析<br />3. 自然语言问答助手<br />4. 幻觉校验机制<br />5. 报告导出功能                                                    | AI功能可用，无数据幻觉             |
| 阶段四：优化上线   | 1周  | 1. 全量测试与bug修复<br />2. 性能优化<br />3. 部署上线与数据初始化                                                                                                       | 系统正式可用                       |

**总开发周期：约7周**

---

## 十二、风险与规避方案

| 风险点            | 影响等级 | 规避方案                                                                           |
| ------------------- | ---------- | ------------------------------------------------------------------------------------ |
| Baostock接口变更  | 中       | 封装适配器层，接口变更仅修改适配器；保留数据本地备份，接口故障时不影响历史数据查询 |
| AkShare被反爬封禁 | 中       | 严格按需调用+长延时+单线程；增加熔断机制；预留巨潮PDF解析作为备选附注数据源        |
| 巨潮公告接口限流  | 低       | 每日低峰期增量同步，控制请求频率；备用AkShare公告接口                              |
| AI生成数据幻觉    | 高       | 严格RAG架构，数值强制校验，输出边界硬约束，所有结论强制溯源                        |
| 数据准确性错误    | 高       | 内置勾稽关系校验，异常数据自动标记；人工抽检机制，定期与官方公告核对               |
| 数据库性能下降    | 低       | 合理建索引，大表按年份分区；定期执行表优化与碎片整理                               |

---