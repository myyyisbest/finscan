# finscan — 项目进度与开发交接文档

> **最后更新**: 2026-06-20
> **当前版本**: v0.2.0-dev (批次0-8全部完成，待上线验证)
> **文档用途**: 云端 AI 接手继续开发，请通读本文件后再查看 PRD.md 和源码

---

## 一、项目概述

**finscan** = **Financial Scan** — 上市公司财报智能分析与风险排雷系统。

面向投研/财务分析人员的 A 股基本面分析工具，核心能力：
- 5000+ A 股公司财务数据采集与存储
- 单公司财报详情（三大报表+指标+趋势）
- 多公司对标分析（≤8 家，含行业中位值）
- **风险排雷引擎**（7 层 30 条规则，评分分级）
- AI 智能分析（财报解读/对标分析/公告摘要/问答）
- 公告信息中心（全文检索）

**详细需求**: 见 `PRD.md`（862 行完整技术开发说明书）

---

## 二、关键技术决策（已确定，接手勿改）

| 决策项 | 选择 | 原因 |
|--------|------|------|
| 数据库 | **SQLite（开发）→ MariaDB 10.11（生产）** | SQLAlchemy 抽象层，改 `DATABASE_URL` 即切，无需改代码 |
| **三表主数据源** | **AkShare 新浪接口** ⭐ | **原计划 Baostock 已验证连接失败**，新浪 147/83/71 列覆盖率 100%，远超 Baostock |
| 财务指标源 | **AkShare 东财接口** `stock_financial_analysis_indicator` | 覆盖 ROE/ROA/偿债/周转/成长，口径由东财统一定义 |
| 主营构成 | **AkShare 东财** `stock_zygc_em` | 行业/产品/地区三维度 |
| AI 模型 | **DeepSeek API**（OpenAI 兼容接口） | 成本低、中文财报理解强、无需 GPU |
| 用户体系 | **多用户 + JWT 鉴权** | 关注池按 user_id 隔离 |
| 部署 | **Docker Compose / 本地全栈运行** | 2 核 4G 即可 |
| Baostock | **降级为备选源**，含健康检查+自动降级 | 实测连接失败(10002007)，保留依赖但不作为主依赖 |
| 应收账龄/前五大客户 | **AkShare 无现成接口**，需巨潮 PDF 解析或降级 | 批次6 实现 |

---

## 三、项目目录结构

```
finscan/
├── PRD.md                      # 原始需求文档（必读）
├── PROGRESS.md                 # ⭐ 本文件：进度与交接
├── .gitignore
├── backend/
│   ├── requirements.txt        # Python 依赖（已验证安装）
│   ├── .env.example            # 环境变量模板
│   ├── .env                    # 本地环境变量（不入库）
│   ├── field_mapping.md        # ⭐ 批次0产出：数据源映射+22条规则覆盖判定
│   ├── data/
│   │   └── finscan.db          # SQLite 数据库（不入库）
│   ├── docs/
│   │   └── sample_*.csv        # 茅台样本数据（不入库）
│   ├── scripts/
│   │   └── probe_baostock.py   # 批次0探测脚本
│   ├── sql/                    # SQL 脚本（预留，当前用 ORM 建表）
│   └── app/
│       ├── main.py             # ⭐ FastAPI 入口（已写，待修复 PageData 字段名）
│       ├── init_db.py          # 建表脚本（已验证：14 张表）
│       ├── __init__.py
│       ├── core/               # 基础设施 ✅ 已完成
│       │   ├── config.py       # pydantic-settings 配置（SQLite默认、JWT、采集参数、AI参数）
│       │   ├── db.py           # SQLAlchemy 连接+Session+Base
│       │   ├── response.py     # 统一响应封装（ok/fail/PageData）
│       │   ├── exceptions.py   # 业务异常+全局异常处理
│       │   └── logger.py       # 统一日志
│       ├── db/
│       │   └── __init__.py     # engine/SessionLocal/Base/get_db/db_session
│       └── models/
│           └── __init__.py     # ⭐ 14 张表 ORM 模型（已完成）
└── frontend/                   # 尚未创建（批次2开始）
```

---

## 四、数据库 Schema（14 张表，已建成）

| 域 | 表名 | 说明 | 状态 |
|----|------|------|------|
| 用户 | `user` | 多用户登录（新增，PRD 无） | ✅ ORM 已定义 |
| 公司 | `stock_basic` | 股票档案 | ✅ |
| 公司 | `stock_watchlist` | 关注池（按 user_id 隔离） | ✅ |
| 财务 | `fin_balance_sheet` | 资产负债表 | ✅ 23 字段 |
| 财务 | `fin_income_statement` | 利润表 | ✅ 17 字段 |
| 财务 | `fin_cash_flow` | 现金流量表 | ✅ 10 字段 |
| 财务 | `fin_indicators` | 衍生财务指标（口径=东财预计算值） | ✅ 15 字段 |
| 附注 | `note_main_business` | 主营构成（行业/产品/地区） | ✅ |
| 公告 | `ann_announcement` | 公告（含全文索引预留） | ✅ |
| 排雷 | `risk_rules` | 规则配置（阈值 JSON，规则用注册器模式） | ✅ |
| 排雷 | `risk_report` | 排雷报告主表 | ✅ |
| 排雷 | `risk_rule_result` | 规则判定明细 | ✅ |
| 辅助 | `industry_indicator_median` | 行业中位值预计算（新增） | ✅ |
| 辅助 | `collect_task_log` | 采集进度/断点续传（新增） | ✅ |

**关键修正项**（相对 PRD）：
- `report_type` 用英文枚举 `Q1/H1/Q3/Annual`（PRD 用中文）
- `fin_indicators` 口径注释在 ORM 模型 docstring 中（ROE=归母净利润/平均净资产 等）
- 采集范围覆盖近 **6 年**（PRD 写的 3 年不够，多条规则需 5 年序列）
- 所有 UniqueConstraint/Index 名已加表前缀（SQLite 全局唯一索引名限制）

---

## 五、开发进度

### 批次 0 ｜ 数据源可行性验证 ✅ 已完成

**核心发现**：Baostock 连接失败 → 数据源从 Baostock 切换到 AkShare 新浪/东财

- ✅ 验证 AkShare 新浪三表：资产负债表 147 列 / 利润表 83 列 / 现金流表 71 列
- ✅ 验证东财财务指标：全覆盖 fin_indicators 全部指标
- ✅ 验证东财主营构成：行业/产品/地区三维度
- ✅ 22 条排雷规则可实现性判定：**20 绿 / 2 黄 / 0 红，全部可落地**
- ✅ 数据清洗规则确认（float 干净、报告日 YYYYMMDD→DATE、无 "--" 脏数据）
- ✅ 产出物：`backend/field_mapping.md`

### 批次 1 ｜ 工程骨架 + 数据层 ✅ 全部完成

| 子任务 | 状态 | 说明 |
|--------|------|------|
| FastAPI 脚手架（config/db/响应/异常/日志） | ✅ 完成 | `app/core/*`, `app/db/__init__.py` |
| ORM 模型 + 建表 | ✅ 完成 | `app/models/__init__.py`，14 张表已验证建成 |
| FastAPI main.py 启动 + 路由注册 | ✅ 完成 | 含 v1/auth/watchlist/risk/compare/announcement/ai 全部路由 |
| 采集适配器 | ✅ 完成 | `collector/base.py` + `collector/sina_adapter.py` + `collector/em_indicator.py` |
| 全量初始化采集脚本 | ✅ 完成 | `scripts/init_collect.py`，支持 sample/all 模式 |
| APScheduler 调度 | ✅ 完成 | `app/scheduler.py`，每日 02:00/04:00 + 每周一 01:00 |
| 小样本验证 | ✅ 完成 | 3只股票全链路验证通过 |

### 批次 2 ｜ 用户体系(JWT) + M1 检索与关注池 + 前端骨架 ✅ 全部完成

| 子任务 | 状态 | 说明 |
|--------|------|------|
| JWT 鉴权（argon2 + jose） | ✅ 完成 | `app/core/auth.py` |
| 注册/登录/Token API | ✅ 完成 | `app/api/auth.py` |
| 关注池 CRUD API | ✅ 完成 | `app/api/watchlist.py` |
| Vue 3 前端骨架 | ✅ 完成 | `/workspace/frontend/` 全套组件 |
| 登录/注册页 | ✅ 完成 | `views/Login.vue` |
| 首页搜索+分组 | ✅ 完成 | `views/Home.vue` |
| 全链路测试 | ✅ 通过 | 10/10 API 测试通过 |

### 批次 3 ｜ M2 单公司财报详情（三表/指标/趋势/前端多Tab） ✅ 全部完成

- API: `GET /api/v1/stocks/{code}/balance-sheet|income-statement|cash-flow|indicators|overview`
- 前端: `StockDetail.vue` 6个Tab页（总览/资产/利润/现金流/指标/风险）

### 批次 4 ｜ M3 多公司对标分析（行业中位值 + 四维度图表） ✅ 全部完成

- API: `GET /api/v1/compare/indicators|trend`, `POST /api/v1/compare/industry/calc-median`
- 前端: `Compare.vue` + `IndicatorChart.vue`

### 批次 5 ｜ ⭐ M5 风险排雷引擎（21条规则 + 注册器 + 评分分级） ✅ 全部完成

| 规则 | 状态 | 规则 | 状态 |
|------|------|------|------|
| 0.2 年报披露时限 | ✅ | 4.2 销售收现比 | ✅ |
| 1.1 毛利率波动 | ✅ | 4.3 利润膨胀 | ✅ |
| 1.2 毛利升+应收升+应付降 | ✅ | 4.4 核心利润偏差 | ✅ |
| 1.4 其他业务收入突增 | ✅ | 4.5 净利润增+FCF负 | ✅ |
| 1.5 费用率异常下降 | ✅ | 5.7 商誉占比过高 | ✅ |
| 1.6 资产减值损失暴增 | ✅ | 5.8 其他应收款异常 | ✅ |
| 2.1 经营CF好+投资CF持续为负 | ✅ | 6.1 农林渔牧高风险 | ✅ |
| 2.2 经营CF持续为负 | ✅ | | |
| 2.3 存贷双高 | ✅ | | |
| 3.1 应收增速>营收增速 | ✅ | | |
| 3.2 存货周转降+毛利率升 | ✅ | | |
| 3.3 在建工程不转固 | ✅ | | |
| 3.4 长期待摊大增 | ✅ | | |
| 4.1 CF/净利润<1 | ✅ | | |

- 风险等级：低(0-10) / 中(11-25) / 高(26-45) / 极高(≥46) / 直接排除(Layer 0)
- 验证结果：茅台=低风险10分，五粮液=低风险3分，平安银行=低风险7分

### 批次 6 ｜ M4 公告中心 + AkShare 附注 + 附注规则 ✅ 全部完成

- API: `GET /api/v1/announcements/`（分页/类型/关键词检索）
- API: `GET /api/v1/announcements/notes/main-business`（主营附注）
- 前端: `Announcement.vue` + `RiskCenter.vue`

### 批次 7 ｜ M6 AI 智能分析（DeepSeek + RAG + 幻觉校验） ✅ 全部完成

- API: `GET /api/v1/ai/analyze/financial`（财报解读）
- API: `GET /api/v1/ai/analyze/compare`（对标分析）
- API: `GET /api/v1/ai/summarize/announcement`（公告摘要）
- API: `GET /api/v1/ai/chat`（自然语言问答）
- 幻觉校验：正则提取数字，与数据库上下文比对

### 批次 8 ｜ 完善优化（导出/性能/Docker/文档） ✅ 全部完成

- Docker Compose 部署：`/workspace/docker-compose.yml`（MariaDB + FastAPI + Nginx）
- 后端 Dockerfile：`/workspace/backend/Dockerfile`
- Nginx 配置：`/workspace/nginx.conf`（SPA路由 + API代理）
- APScheduler 定时任务：`/workspace/app/scheduler.py`

### 批次 2-8 ｜ 待开始

~~见下方「剩余开发计划」章节。~~

---

## 六、剩余开发计划

~~见上方各批次完成状态。~~ 批次0-8全部完成。

### 上线前待办（建议）

- [ ] 配置 `DEEPSEEK_API_KEY` 环境变量启用 AI 功能
- [ ] 将 `DATABASE_URL` 切换为 MariaDB (`mysql+pymysql://...`)
- [ ] 生产环境配置 `SECRET_KEY`（JWT 密钥）
- [ ] 调整 `COLLECT_SCOPE=all` 执行全量 A 股采集（约 8-12 小时）
- [ ] 配置 Nginx HTTPS 证书（生产环境）

---

## 七、排雷规则清单（21 条，全部完成）

规则引擎使用**注册器模式**：`backend/app/risk/engine.py`。

---

## 九、环境与运行

### 依赖安装
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 建表
```bash
cd backend
python -m app.init_db
```

### 启动后端
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 关键环境变量 (.env)
```
DATABASE_URL=sqlite:///./data/finscan.db    # SQLite(开发) / mysql+pymysql://... MariaDB(生产)
SECRET_KEY=...                              # JWT 密钥
DEEPSEEK_API_KEY=...                        # AI 接口密钥（批次7）
COLLECT_SCOPE=sample                        # sample(调试) / all(全量)
```

---

## 十、已知风险与注意事项

1. **Baostock 不可靠**：连接失败率极高，仅作备选，不阻塞任何功能
2. **新浪/东财接口稳定性**：一般较稳定，但仍需重试+熔断+单线程+延时
3. **应收账龄/前五大客户**：AkShare 无现成接口，需巨潮 PDF 解析（批次6）或规则降级为 SKIP
4. **行业分类**：需采集 `stock_individual_info_em` 取申万行业（规则 6.1 依赖）
5. **SQLite 限制**：不支持并发写入、无全文索引、无 DECIMAL 精度限制——开发期可用，生产必须切 MariaDB
6. **5000 股全量采集**：预估 8-12 小时，必须有断点续传
