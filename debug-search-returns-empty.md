# Debug Session: search-returns-empty

**Status**: [FIXED — 待用户确认]
**Symptom**: 用户访问 http://localhost:3005 后,在搜索框输入"航天电子"无数据加载
**Expected**: 应返回航天电子(600879.SH)及匹配的公司列表/财务数据
**Env**: Linux, Backend Uvicorn :8000, Frontend Vite :3005, PostgreSQL 17

## Hypotheses (验证结果)

| ID  | 假设                           | 状态         | 证据                                                                |
| --- | ------------------------------ | ------------ | ------------------------------------------------------------------- |
| H1  | 前后端联通问题(代理/CORS)      | ❌ 排除       | 后端日志: 200 OK, Vite 代理 3005→8000 正常                            |
| H2  | 搜索接口路由不匹配             | ❌ 排除       | `GET /api/v1/stocks/search?keyword=航天电子` 返回 200 OK             |
| H3  | 数据未入库                     | ❌ 排除       | psql 查询: stock_basic 有 3 条记录(600879/300136/002149)             |
| H4  | 关键字/字段映射错误            | ❌ 排除       | 后端用 `stock_name LIKE %keyword%` 匹配中文名,逻辑正确                |
| **H5**  | **前端 code 字段判断不匹配**   | ✅ **命中**   | **后端 `ok()` 返回 `code=0`,前端 13 处判断 `code === 200` — 永远拿不到数据** |

## 根因
后端 `app/core/response.py` 成功响应字段 `code=0`,前端 `GlobalSearch.vue` 等 13 处判断 `code === 200`,**业务码约定不一致**,前端永远走"非 200"分支,不渲染下拉项。

## 修复 (第一轮: code 字段)
- 文件: [response.py](file:///home/yyxj/project/finscan/backend/app/core/response.py)
- 改动: `ok()` 与 `Response` 的 `code` 默认值从 `0` 改为 `200` (3 处)
- 错误码 1001/2001/3001/5000 保持不变 (前端的 3001 跳登录逻辑正确)
- uvicorn 重启后验证: `curl /api/v1/stocks/search?keyword=航天电子` 返回 `{"code":200,...,"data":{"items":[{"stock_code":"600879.SH","stock_name":"航天电子"}]}}`

## 第二轮: a-auto-complete 需要 value 字段
- 文件: [GlobalSearch.vue](file:///home/yyxj/project/finscan/frontend/src/components/GlobalSearch.vue)
- 改动: items 映射时补上 `value: stock_code` (a-auto-complete 依赖此字段)

## 第三轮: watchlist/groups 数据结构不一致
- 现象: 自选区卡片一直显示"加载中"旋转图标; 用户说"股票检索页搜索没反应"(全局 JS 受 watchlist 区域报错牵连, 整个右侧冻结)
- 根因: 后端 `/api/v1/watchlist/groups` 返回 `data: {groups: [...], total: N}`, 前端期望 `data: WatchlistGroup[]`
  - 前端 `groups.value = response.data.data` → 拿到对象
  - `currentStocks` computed 调用 `groups.value.flatMap(...)` → 抛 TypeError
  - computed 抛错导致右侧 watchlist 区域 render 异常, 整个 a-spin spinning 状态被冻结
- 修复: [Home.vue](file:///home/yyxj/project/finscan/frontend/src/views/Home.vue) `loadGroups` 改 `response.data.data.groups || []`

## 第四轮: Sidebar "首页"和"股票检索"菜单 key 重复
- 现象: 点击"股票检索"和点击"首页"都跳到 `/`, 用户感觉两个页面"没区别"
- 根因: [Sidebar.vue](file:///home/yyxj/project/finscan/frontend/src/layout/Sidebar.vue) 中两个 menu-item 的 `key` 都是 `'/'`
- 修复:
  1. Sidebar: "股票检索" 菜单 key 改为 `/search`
  2. [router/index.ts](file:///home/yyxj/project/finscan/frontend/src/router/index.ts) 增加 `path: 'search'` 路由
  3. 新建 [StockSearch.vue](file:///home/yyxj/project/finscan/frontend/src/views/StockSearch.vue) 独立页面(搜索框 + 列表 + 加入自选按钮)

## 第五轮: StockSearch.vue 内部函数同名递归导致栈溢出
- 现象: 点击「加入自选」按钮页面卡死无响应
- 根因: `StockSearch.vue` 内部 `const addToWatchlist = async ...` 遮蔽了顶部 `import { addToWatchlist } from '@/api/watchlist'`, 函数体里 `await addToWatchlist({...})` 实际调用本函数自己 → 无限递归 → 栈溢出
- 修复: 顶部 import 改名为 `addToWatchlist as addStockToWatchlist`, 函数体用别名调用

## 待清理
- 本次 debug session 文档 (确认后删除)
