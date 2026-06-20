# finscan — 项目进度与开发交接文档

> **最后更新**: 2026-06-20
> **当前版本**: v0.1.0-dev (批次0完成，批次1进行中)
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

### 批次 1 ｜ 工程骨架 + 数据层 🔄 进行中（约 60%）

| 子任务 | 状态 | 说明 |
|--------|------|------|
| FastAPI 脚手架（config/db/响应/异常/日志） | ✅ 完成 | `app/core/*`, `app/db/__init__.py` |
| ORM 模型 + 建表 | ✅ 完成 | `app/models/__init__.py`，14 张表已验证建成 |
| **FastAPI main.py 启动** | 🔧 需修复 | `response.py` 中 `PageData.list` → `PageData.items` 已改，但未验证启动 |
| **采集适配器** | ❌ 未开始 | 需要 `collector/base.py` + `collector/sina_adapter.py` + `collector/em_indicator.py` + `collector/em_zygc.py` |
| **全量初始化采集脚本** | ❌ 未开始 | 断点续传 + 进度表 + 勾稽校验 |
| **APScheduler 调度** | ❌ 未开始 | 定时增量同步骨架 |
| **小样本验证** | ❌ 未开始 | 3-5 只股票跑通采集→入库→查询全链路 |

### 批次 2-8 ｜ 待开始

见下方「剩余开发计划」章节。

---

## 六、接手后立即要做的 3 件事（按优先级）

### 1. 修复 FastAPI 启动并验证脚手架 ✅ 可快速完成

`app/core/response.py` 中 `PageData` 的 `list` 字段已改为 `items`（因 Python 3.12 类型注解冲突）。
需运行验证：
```bash
cd backend && . .venv/bin/activate
python -m app.init_db          # 确认建表正常
uvicorn app.main:app --port 8000 --reload  # 确认 API 启动
curl http://127.0.0.1:8000/     # 返回 {"app":"finscan","status":"running",...}
```

### 2. 实现采集适配器 ⭐ 核心工作

创建 `backend/app/collector/` 目录，实现 4 个文件：

```
collector/
├── __init__.py
├── base.py              # 适配器基类：重试(3次) + 随机延时(1-3s) + 熔断 + 日志
├── sina_adapter.py      # 新浪三表：stock_financial_report_sina（主数据源）
├── em_indicator.py     # 东财指标：stock_financial_analysis_indicator
└── em_zygc.py          # 东财主营构成：stock_zygc_em
```

**新浪三表字段映射表**见 `backend/field_mapping.md` 第二章。

关键实现细节：
- 新浪 `stock_financial_report_sina(stock='sh600519', symbol='资产负债表')` 返回 DataFrame，列为中文名
- 字段映射：`fin_balance_sheet` 的 `monetary_funds` ← 新浪列 `货币资金`，以此类推
- `report_type` 判定：`报告日` 的月份 → 03月=Q1, 06月=H1, 09月=Q3, 12月=Annual
- `报告日` 格式：`"20231231"` (str) → `datetime.date(2023,12,31)`
- 数值已是 float，无需额外清洗
- 每只股票每张表耗时约 2-3 秒（含延时），5000 只全量约 8-12 小时

### 3. 全量初始化采集脚本

`backend/scripts/init_collect.py`：遍历全 A 股 → 调采集适配器 → 写入 DB → 记录 `collect_task_log` 进度 → 支持中断后跳过 `status='done'` 的记录继续。

---

## 七、剩余开发计划（8 批次）

| 批次 | 内容 | 预估 | 状态 |
|------|------|------|------|
| **0** | 数据源可行性验证 | 3天 | ✅ 完成 |
| **1** | 工程骨架 + 数据层（采集器 + 建库 + 调度） | 1.5周 | 🔄 60% |
| **2** | 用户体系(JWT) + M1 检索与关注池 + 前端骨架 | 1周 | 待开始 |
| **3** | M2 单公司财报详情（三表/指标/趋势/前端多Tab） | 1.5周 | 待开始 |
| **4** | M3 多公司对标分析（行业中位值 + 四维度图表） | 1周 | 待开始 |
| **5** | ⭐ M5 风险排雷引擎（22条规则 + 注册器 + 单测 + 造假回归） | 2周 | 待开始 |
| **6** | M4 公告中心 + AkShare 附注 + 附注规则 | 1周 | 待开始 |
| **7** | M6 AI 智能分析（DeepSeek + RAG + 幻觉校验） | 1.5周 | 待开始 |
| **8** | 完善优化（导出/性能/Docker/文档） | 1周 | 待开始 |

**总预估**: 8-10 周（单人全栈）

---

## 八、排雷规则清单（22 条，批次5 实现）

规则引擎用**注册器模式**：每条规则 = 一个 Python 文件 + `@register_rule` 装饰器。
规则阈值存 `risk_rules` 表（JSON），计算逻辑在代码里（诚实表述）。
每条规则强制单元测试。

完整规则表见 `PRD.md` 第六章。可实现性判定见 `backend/field_mapping.md` 第五章。

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
