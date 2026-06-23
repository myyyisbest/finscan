<template>
  <div class="stock-detail">
    <!-- 左侧：基础信息 -->
    <aside class="info-panel">
      <div class="info-header">
        <h2 class="stock-name">
          {{ stockInfo.stock_name || code }}
          <a-tag v-if="stockInfo.is_st" color="red">ST</a-tag>
        </h2>
        <div class="stock-code">{{ code }}<a-tag size="small" color="blue" style="margin-left:8px">{{ stockInfo.market || '-' }}</a-tag></div>
      </div>

      <div class="info-actions">
        <a-button v-if="watchlistStocks.length > 0" type="primary" block @click="showAddModal = true">
          <StarOutlined /> 加入自选
        </a-button>
        <a-button v-else type="primary" block @click="quickAddWatchlist">
          <PlusOutlined /> 加入自选
        </a-button>
      </div>

      <a-divider style="margin: 12px 0" />

      <div class="info-section">
        <div class="section-title">公司资料</div>
        <div class="info-grid">
          <div class="info-item"><span class="lbl">所属行业</span><span class="val">{{ stockInfo.industry || '-' }}</span></div>
          <div class="info-item"><span class="lbl">总股本</span><span class="val">{{ formatShare(basic.total_share) }}</span></div>
          <div class="info-item"><span class="lbl">流通股本</span><span class="val">{{ formatShare(basic.float_share) }}</span></div>
          <div class="info-item"><span class="lbl">上市日期</span><span class="val">{{ stockInfo.list_date || '-' }}</span></div>
        </div>
      </div>

      <a-divider style="margin: 12px 0" />

      <div class="info-section">
        <div class="section-title">实时行情</div>
        <div class="quote-price">
          <span class="price" :class="priceClass(quote.change_pct)">{{ quote.latest_price || '-' }}</span>
          <span class="change" :class="priceClass(quote.change_pct)">
            {{ quote.change_amount || '0' }}
            ({{ quote.change_pct || '0' }}%)
          </span>
        </div>
        <div class="quote-date">行情时间: {{ quote.quote_date || '-' }}</div>
        <div class="info-grid" style="margin-top: 8px">
          <div class="info-item"><span class="lbl">今开</span><span class="val">{{ quote.open_price || '-' }}</span></div>
          <div class="info-item"><span class="lbl">昨收</span><span class="val">{{ quote.pre_close || '-' }}</span></div>
          <div class="info-item"><span class="lbl">最高</span><span class="val">{{ quote.high_price || '-' }}</span></div>
          <div class="info-item"><span class="lbl">最低</span><span class="val">{{ quote.low_price || '-' }}</span></div>
          <div class="info-item"><span class="lbl">成交量</span><span class="val">{{ formatVolume(quote.volume) }}</span></div>
          <div class="info-item"><span class="lbl">成交额</span><span class="val">{{ formatVolume(quote.turnover) }}</span></div>
        </div>
      </div>

      <a-divider style="margin: 12px 0" />

      <div class="info-section">
        <div class="section-title">估值与规模</div>
        <div class="info-grid">
          <div class="info-item"><span class="lbl">市盈率(动)</span><span class="val">{{ quote.pe || '-' }}</span></div>
          <div class="info-item"><span class="lbl">市盈率(TTM)</span><span class="val">{{ quote.pe_ttm || '-' }}</span></div>
          <div class="info-item"><span class="lbl">市净率</span><span class="val">{{ quote.pb || '-' }}</span></div>
          <div class="info-item"><span class="lbl">市销率</span><span class="val">{{ quote.ps_ttm || '-' }}</span></div>
          <div class="info-item" style="grid-column: span 2"><span class="lbl">总市值</span><span class="val">{{ formatMoney(quote.total_market_cap) }}</span></div>
          <div class="info-item" style="grid-column: span 2"><span class="lbl">流通市值</span><span class="val">{{ formatMoney(quote.float_market_cap) }}</span></div>
        </div>
      </div>
    </aside>

    <!-- 右侧：Tab 内容 -->
    <main class="content-panel">
      <a-tabs v-model:active-key="activeTab" class="content-tabs">
        <!-- 主要指标: 复现东财 财务报表 主要指标页(全量50+字段 × 10期) -->
        <a-tab-pane key="main" tab="主要指标">
          <a-spin :spinning="mainIndicatorsLoading">
            <a-alert v-if="mainIndicatorGroups.length === 0" type="info" message="暂无主要指标数据" show-icon />
            <template v-else>
              <div class="toolbar">
                <a-radio-group v-model:value="mainPeriodCount" size="small" button-style="solid" @change="loadMainIndicators">
                  <a-radio-button :value="10">近10期</a-radio-button>
                  <a-radio-button :value="20">近20期</a-radio-button>
                </a-radio-group>
                <span class="toolbar-tip">数据来源: 新浪财经 stock_financial_analysis_indicator</span>
              </div>

              <div class="em-main-table">
                <div class="em-table-row em-header-row">
                  <div class="em-cell em-label-cell">指标</div>
                  <div v-for="p in mainPeriods" :key="p" class="em-cell em-period-cell">{{ p }}</div>
                </div>
                <template v-for="(group, gIdx) in mainIndicatorGroups" :key="group.name">
                  <div class="em-group-row" :class="{ alt: gIdx % 2 === 1 }">{{ group.name }}</div>
                  <div
                    v-for="item in group.items"
                    :key="item.key"
                    class="em-table-row"
                  >
                    <div class="em-cell em-label-cell">{{ item.label }}</div>
                    <div
                      v-for="p in mainPeriods"
                      :key="p"
                      class="em-cell em-num-cell"
                      :class="valueClass(item.values[p], item.key)"
                    >
                      {{ formatMainValue(item.values[p], item.unit) }}
                    </div>
                  </div>
                </template>
              </div>
            </template>
          </a-spin>
        </a-tab-pane>

        <!-- 财务摘要: 多年对比 -->
        <a-tab-pane key="summary" tab="财务摘要">
          <a-spin :spinning="summaryLoading">
            <a-alert v-if="summaryYears.length === 0" type="info" message="暂无多年财务数据" show-icon />
            <template v-else>
              <div class="toolbar">
                <a-radio-group v-model:value="summaryReportType" size="small" button-style="solid" @change="loadSummary">
                  <a-radio-button value="Annual">年度报告</a-radio-button>
                  <a-radio-button value="Q1">Q1</a-radio-button>
                  <a-radio-button value="H1">H1</a-radio-button>
                  <a-radio-button value="Q3">Q3</a-radio-button>
                </a-radio-group>
                <span class="toolbar-tip">数据来源: 新浪财经</span>
              </div>

              <a-card size="small" title="利润表" class="fin-card">
                <a-table
                  :columns="incomeCols"
                  :data-source="incomeRows"
                  :pagination="false"
                  size="small"
                  bordered
                  row-key="label"
                />
              </a-card>

              <a-card size="small" title="资产负债表" class="fin-card">
                <a-table
                  :columns="balanceCols"
                  :data-source="balanceRows"
                  :pagination="false"
                  size="small"
                  bordered
                  row-key="label"
                />
              </a-card>

              <a-card size="small" title="现金流量表" class="fin-card">
                <a-table
                  :columns="cashflowCols"
                  :data-source="cashflowRows"
                  :pagination="false"
                  size="small"
                  bordered
                  row-key="label"
                />
              </a-card>
            </template>
          </a-spin>
        </a-tab-pane>

        <!-- 指标趋势 -->
        <a-tab-pane key="indicators" tab="指标趋势">
          <a-spin :spinning="indicatorLoading">
            <a-row :gutter="12" style="margin-bottom: 12px">
              <a-col :span="4" v-for="card in indicatorCards" :key="card.key">
                <a-card size="small" class="indicator-stat-card">
                  <a-statistic :title="card.label" :value="card.value" :precision="card.precision" :value-style="{ color: card.color, fontSize: '20px' }" />
                </a-card>
              </a-col>
            </a-row>
            <a-tabs v-model:active-key="indicatorChartKey" size="small">
              <a-tab-pane key="profit" tab="盈利能力">
                <div ref="profitChartRef" class="indicator-chart"></div>
              </a-tab-pane>
              <a-tab-pane key="growth" tab="成长能力">
                <div ref="growthChartRef" class="indicator-chart"></div>
              </a-tab-pane>
              <a-tab-pane key="operate" tab="运营能力">
                <div ref="operateChartRef" class="indicator-chart"></div>
              </a-tab-pane>
              <a-tab-pane key="debt" tab="偿债能力">
                <div ref="debtChartRef" class="indicator-chart"></div>
              </a-tab-pane>
            </a-tabs>
          </a-spin>
        </a-tab-pane>

        <!-- 公告信息 -->
        <a-tab-pane key="announcement" tab="公告信息">
          <a-spin :spinning="annLoading">
            <a-space style="margin-bottom: 12px">
              <a-select v-model:value="annTypeFilter" placeholder="全部类型" style="width: 180px" allow-clear @change="loadAnnouncements">
                <a-select-option v-for="t in annTypeOptions" :key="t" :value="t">{{ t }}</a-select-option>
              </a-select>
              <a-input-search v-model:value="annKeyword" placeholder="搜索公告标题" style="width: 240px" @search="loadAnnouncements" />
            </a-space>
            <a-list size="small" :data-source="announcements" item-layout="vertical">
              <template #renderItem="{ item }">
                <a-list-item class="ann-item" @click="showAnnDetail(item)">
                  <a-list-item-meta>
                    <template #title>
                      <span class="ann-title">{{ item.ann_title }}</span>
                    </template>
                    <template #description>
                      <a-space>
                        <a-tag color="blue">{{ item.ann_type }}</a-tag>
                        <span class="ann-date">{{ item.publish_date }}</span>
                        <a-tag v-if="item.source" size="small">{{ item.source }}</a-tag>
                      </a-space>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
            <a-empty v-if="!annLoading && announcements.length === 0" description="暂无公告" />
            <a-pagination
              v-if="annTotal > annPageSize"
              v-model:current="annPage"
              :page-size="annPageSize"
              :total="annTotal"
              show-quick-jumper
              size="small"
              style="margin-top: 12px; text-align: right"
              @change="loadAnnouncements"
            />
          </a-spin>
        </a-tab-pane>
      </a-tabs>
    </main>

    <!-- 公告详情弹窗 -->
    <a-modal
      v-model:open="annDetailVisible"
      :title="currentAnn?.ann_title"
      width="700px"
      :footer="null"
    >
      <div v-if="currentAnn">
        <a-descriptions size="small" :column="2">
          <a-descriptions-item label="股票代码">{{ currentAnn.stock_code }}</a-descriptions-item>
          <a-descriptions-item label="公告类型">{{ currentAnn.ann_type }}</a-descriptions-item>
          <a-descriptions-item label="发布日期">{{ currentAnn.publish_date }}</a-descriptions-item>
          <a-descriptions-item label="来源">{{ currentAnn.source }}</a-descriptions-item>
        </a-descriptions>
        <a-divider />
        <a v-if="currentAnn.pdf_url" :href="currentAnn.pdf_url" target="_blank" type="primary">
          查看原文 / 下载 PDF ↗
        </a>
        <div v-else style="color: #999">暂无原文链接</div>
      </div>
    </a-modal>

    <!-- 加入自选弹窗 -->
    <a-modal v-model:open="showAddModal" title="加入自选" @ok="confirmAddWatchlist" :confirm-loading="addLoading">
      <a-form layout="vertical">
        <a-form-item label="分组">
          <a-select v-model:value="addForm.group_name" placeholder="选择分组">
            <a-select-option v-for="g in groups" :key="g.group_name" :value="g.group_name">{{ g.group_name }}</a-select-option>
            <a-select-option value="__new__">+ 新建分组</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="addForm.group_name === '__new__'" label="新分组名">
          <a-input v-model:value="addForm.new_group_name" placeholder="输入新分组名" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { message } from 'ant-design-vue'
import {
  getStockOverview,
  getBalanceSheet,
  getIncomeStatement,
  getCashFlow,
  getIndicators,
  getMainIndicators,
} from '@/api/stock'
import { getAnnouncements } from '@/api/announcement'
import { getWatchlistGroups, addToWatchlist as addStock, createGroup } from '@/api/watchlist'

const route = useRoute()
const code = computed(() => route.params.code as string)

const activeTab = ref('main')
const summaryReportType = ref('Annual')
const summaryLoading = ref(false)
const summaryYears = ref<string[]>([])

// ===== 主要指标 Tab(东财『主要指标』复刻) =====
const mainIndicatorsLoading = ref(false)
const mainPeriods = ref<string[]>([])
const mainIndicatorGroups = ref<{ name: string; items: any[] }[]>([])
const mainPeriodCount = ref(10)

const incomeRows = ref<any[]>([])
const balanceRows = ref<any[]>([])
const cashflowRows = ref<any[]>([])

const indicatorLoading = ref(false)
const indicatorChartKey = ref('profit')
const profitChartRef = ref<HTMLElement | null>(null)
const growthChartRef = ref<HTMLElement | null>(null)
const operateChartRef = ref<HTMLElement | null>(null)
const debtChartRef = ref<HTMLElement | null>(null)
let profitChart: echarts.ECharts | null = null
let growthChart: echarts.ECharts | null = null
let operateChart: echarts.ECharts | null = null
let debtChart: echarts.ECharts | null = null

const annLoading = ref(false)
const announcements = ref<any[]>([])
const annTotal = ref(0)
const annPage = ref(1)
const annPageSize = 20
const annTypeFilter = ref<string | undefined>()
const annKeyword = ref('')
const annTypeOptions = ['定期报告', '业绩预告', '并购重组', '股权激励', '分红派息', '股东大会', '公司治理', '重大事项', '监管问询', '风险提示']
const annDetailVisible = ref(false)
const currentAnn = ref<any>(null)

const stockInfo = ref<any>({})
const basic = ref<any>({})
const quote = ref<any>({})
const overviewLatest = ref<any>({})
const groups = ref<any[]>([])
const watchlistStocks = ref<any[]>([])
const showAddModal = ref(false)
const addLoading = ref(false)
const addForm = ref({ group_name: '', new_group_name: '' })

const incomeCols = computed(() => {
  const cols: any[] = [{ title: '项目', dataIndex: 'label', width: 200, fixed: 'left' }]
  summaryYears.value.forEach(y => cols.push({ title: y, dataIndex: y, align: 'right' as const }))
  return cols
})
const balanceCols = computed(() => incomeCols.value)
const cashflowCols = computed(() => incomeCols.value)

// 关键指标卡片
const indicatorCards = computed(() => [
  { key: 'roe', label: 'ROE (%)', value: overviewLatest.value.roe ?? 0, precision: 2, color: '#1890ff' },
  { key: 'gross', label: '毛利率 (%)', value: overviewLatest.value.gross_margin ?? 0, precision: 2, color: '#13c2c2' },
  { key: 'net', label: '净利率 (%)', value: overviewLatest.value.net_margin ?? 0, precision: 2, color: '#722ed1' },
  { key: 'rev_yoy', label: '营收同比 (%)', value: overviewLatest.value.revenue_yoy ?? 0, precision: 2, color: '#52c41a' },
  { key: 'np_yoy', label: '净利同比 (%)', value: overviewLatest.value.net_profit_yoy ?? 0, precision: 2, color: '#fa8c16' },
  { key: 'debt', label: '资产负债率 (%)', value: overviewLatest.value.debt_to_assets ?? 0, precision: 2, color: '#f5222d' },
])

watch(activeTab, (tab) => {
  if (tab === 'main') loadMainIndicators()
  else if (tab === 'summary') loadSummary()
  else if (tab === 'indicators') loadIndicators()
  else if (tab === 'announcement') loadAnnouncements()
})

watch(mainPeriodCount, () => loadMainIndicators())
watch(summaryReportType, () => loadSummary())

onMounted(async () => {
  await loadOverview()
  await loadWatchlist()
  await loadMainIndicators()
})

onBeforeUnmount(() => {
  profitChart?.dispose()
  growthChart?.dispose()
  operateChart?.dispose()
  debtChart?.dispose()
})

// ========== 数据加载 ==========

const loadOverview = async () => {
  try {
    const res: any = await getStockOverview(code.value)
    if (res.data.code === 200) {
      const d = res.data.data
      stockInfo.value = d.basic || {}
      basic.value = d.basic || {}
      quote.value = d.valuation || {}
      overviewLatest.value = d.latest_annual || {}
    }
  } catch (e) {
    console.error(e)
  }
}

// ===== 主要指标 =====
const _fmt = (n: number) => {
  if (n === null || n === undefined || isNaN(n)) return '-'
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(2) + '万'
  return n.toFixed(2)
}

const formatMainValue = (v: string | null, unit: string) => {
  if (v === null || v === undefined || v === '') return '-'
  const n = Number(v)
  if (isNaN(n)) return v
  if (unit === '元') return _fmt(n)
  // 比率/倍数/天数/次
  if (unit === '%' || unit === '倍' || unit === '天' || unit === '次') {
    // 保留 2 位小数
    if (Math.abs(n) >= 100) return n.toFixed(0)
    if (Math.abs(n) >= 10) return n.toFixed(2)
    return n.toFixed(3)
  }
  return n.toFixed(2)
}

// 给同比/比率上色 (正红负绿, EM 风格)
const valueClass = (v: string | null, key: string) => {
  if (v === null || v === undefined || v === '') return ''
  const n = Number(v)
  if (isNaN(n) || n === 0) return ''
  // 增长类指标: 正红(好) 负绿
  if (
    key.includes('yoy') ||
    key === 'roe' || key === 'roe_weighted' || key === 'roa' ||
    key === 'gross_margin' || key === 'net_margin' || key === 'op_margin' ||
    key === 'revenue_yoy' || key === 'net_profit_yoy' || key === 'equity_yoy' ||
    key === 'total_asset_turnover' || key === 'inventory_turnover' || key === 'ar_turnover'
  ) {
    return n > 0 ? 'val-up' : 'val-down'
  }
  // 越低越好
  if (key === 'debt_to_assets') {
    return n > 60 ? 'val-up' : 'val-down'  // 负债率高偏负
  }
  return ''
}

const loadMainIndicators = async () => {
  mainIndicatorsLoading.value = true
  try {
    const res: any = await getMainIndicators(code.value, mainPeriodCount.value)
    if (res.data.code !== 200) return
    const data = res.data.data || {}
    mainPeriods.value = (data.periods || []).map((p: string) => {
      // 简化为 YY-MM
      return p.substring(2, 7)
    })
    const items: any[] = data.items || []
    // 按 group 分组
    const groupMap: Record<string, any[]> = {}
    items.forEach((it) => {
      if (!groupMap[it.group]) groupMap[it.group] = []
      groupMap[it.group].push(it)
    })
    // 按固定顺序
    const order = ['每股指标', '规模', '成长能力', '盈利能力', '收益质量', '财务风险', '营运能力']
    mainIndicatorGroups.value = order
      .filter((g) => groupMap[g])
      .map((g) => ({ name: g, items: groupMap[g] }))
  } catch (e) {
    console.error(e)
  } finally {
    mainIndicatorsLoading.value = false
  }
}

const loadSummary = async () => {
  summaryLoading.value = true
  try {
    const rt = summaryReportType.value
    // 拉最近 6 期
    const [inc, bal, cf, ind] = await Promise.all([
      getIncomeStatement(code.value, { report_type: rt, page: 1, page_size: 6 }),
      getBalanceSheet(code.value, { report_type: rt, page: 1, page_size: 6 }),
      getCashFlow(code.value, { report_type: rt, page: 1, page_size: 6 }),
      getIndicators(code.value, { page: 1, page_size: 6 }),
    ])
    const incItems = inc.data.data?.items || []
    const balItems = bal.data.data?.items || []
    const cfItems = cf.data.data?.items || []
    summaryYears.value = incItems.map((it: any) => it.report_date).sort()
    const yearCols = summaryYears.value

    const buildRows = (items: any[], fields: { key: string; label: string; type?: 'num' | 'pct' | 'money' }[]) => {
      return fields.map(f => {
        const row: any = { label: f.label }
        items.forEach((it: any) => {
          const colKey = it.report_date
          const v = it[f.key]
          row[colKey] = v != null ? (f.type === 'num' ? Number(v).toLocaleString() : String(v)) : '-'
        })
        return row
      })
    }

    incomeRows.value = buildRows(incItems, [
      { key: 'total_revenue', label: '营业总收入', type: 'num' },
      { key: 'operating_cost', label: '营业成本', type: 'num' },
      { key: 'gross_profit', label: '毛利润', type: 'num' },
      { key: 'gross_margin', label: '毛利率(%)' },
      { key: 'selling_expenses', label: '销售费用', type: 'num' },
      { key: 'admin_expenses', label: '管理费用', type: 'num' },
      { key: 'rd_expenses', label: '研发费用', type: 'num' },
      { key: 'financial_expenses', label: '财务费用', type: 'num' },
      { key: 'operating_profit', label: '营业利润', type: 'num' },
      { key: 'total_profit', label: '利润总额', type: 'num' },
      { key: 'net_profit', label: '净利润', type: 'num' },
      { key: 'net_profit_parent', label: '归母净利润', type: 'num' },
      { key: 'net_profit_deduct', label: '扣非净利润', type: 'num' },
    ])
    balanceRows.value = buildRows(balItems, [
      { key: 'total_assets', label: '总资产', type: 'num' },
      { key: 'total_current_assets', label: '流动资产', type: 'num' },
      { key: 'monetary_funds', label: '货币资金', type: 'num' },
      { key: 'accounts_receivable', label: '应收账款', type: 'num' },
      { key: 'inventory', label: '存货', type: 'num' },
      { key: 'total_liabilities', label: '总负债', type: 'num' },
      { key: 'total_current_liabilities', label: '流动负债', type: 'num' },
      { key: 'short_term_borrowings', label: '短期借款', type: 'num' },
      { key: 'total_equity', label: '所有者权益', type: 'num' },
      { key: 'share_capital', label: '实收资本', type: 'num' },
      { key: 'retained_profits', label: '未分配利润', type: 'num' },
    ])
    cashflowRows.value = buildRows(cfItems, [
      { key: 'operating_cash_inflow', label: '经营现金流入', type: 'num' },
      { key: 'operating_cash_outflow', label: '经营现金流出', type: 'num' },
      { key: 'operating_cash_net', label: '经营现金净额', type: 'num' },
      { key: 'sales_cash_received', label: '销售商品收到现金', type: 'num' },
      { key: 'investing_cash_net', label: '投资现金净额', type: 'num' },
      { key: 'financing_cash_net', label: '筹资现金净额', type: 'num' },
      { key: 'capital_expenditure', label: '资本开支', type: 'num' },
      { key: 'free_cash_flow', label: '自由现金流', type: 'num' },
      { key: 'cash_ending_balance', label: '期末现金余额', type: 'num' },
    ])
    void yearCols
    void ind
  } catch (e) {
    console.error(e)
  } finally {
    summaryLoading.value = false
  }
}

const loadIndicators = async () => {
  indicatorLoading.value = true
  try {
    const res: any = await getIndicators(code.value, { page: 1, page_size: 20 })
    const items = (res.data.data?.items || []).slice().sort((a: any, b: any) => a.report_date.localeCompare(b.report_date))
    const x = items.map((i: any) => i.report_date)

    await nextTick()
    const baseOption = (title: string, series: any[], yName: string) => ({
      title: { text: title, left: 'left', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { data: series.map(s => s.name), top: 0, right: 0 },
      grid: { left: 50, right: 50, bottom: 30, top: 30 },
      xAxis: { type: 'category', data: x, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', name: yName },
      series,
    })

    // 盈利
    const profitSeries = [
      { name: 'ROE(%)', type: 'line', data: items.map((i: any) => Number(i.roe) || 0), smooth: true, itemStyle: { color: '#1890ff' } },
      { name: '净利率(%)', type: 'line', data: items.map((i: any) => Number(i.net_margin) || 0), smooth: true, itemStyle: { color: '#13c2c2' } },
    ]
    if (profitChartRef.value) {
      profitChart = profitChart ?? echarts.init(profitChartRef.value)
      profitChart.setOption(baseOption('盈利能力 (ROE / 净利率)', profitSeries, '%'), true)
    }
    // 成长
    const growthSeries = [
      { name: '营收同比(%)', type: 'bar', data: items.map((i: any) => Number(i.revenue_yoy) || 0), itemStyle: { color: '#52c41a' } },
      { name: '净利同比(%)', type: 'bar', data: items.map((i: any) => Number(i.net_profit_yoy) || 0), itemStyle: { color: '#fa8c16' } },
    ]
    if (growthChartRef.value) {
      growthChart = growthChart ?? echarts.init(growthChartRef.value)
      growthChart.setOption(baseOption('成长能力 (营收/净利同比)', growthSeries, '%'), true)
    }
    // 运营
    const operateSeries = [
      { name: '应收账款周转率', type: 'line', data: items.map((i: any) => Number(i.ar_turnover) || 0), smooth: true, itemStyle: { color: '#722ed1' } },
      { name: '存货周转率', type: 'line', data: items.map((i: any) => Number(i.inventory_turnover) || 0), smooth: true, itemStyle: { color: '#eb2f96' } },
      { name: '总资产周转率', type: 'line', data: items.map((i: any) => Number(i.total_asset_turnover) || 0), smooth: true, itemStyle: { color: '#fa541c' } },
    ]
    if (operateChartRef.value) {
      operateChart = operateChart ?? echarts.init(operateChartRef.value)
      operateChart.setOption(baseOption('运营能力 (周转率)', operateSeries, '次'), true)
    }
    // 偿债
    const debtSeries = [
      { name: '资产负债率(%)', type: 'line', data: items.map((i: any) => Number(i.debt_to_assets) || 0), smooth: true, itemStyle: { color: '#f5222d' } },
      { name: '流动比率', type: 'line', data: items.map((i: any) => Number(i.current_ratio) || 0), smooth: true, itemStyle: { color: '#2f54eb' } },
      { name: '速动比率', type: 'line', data: items.map((i: any) => Number(i.quick_ratio) || 0), smooth: true, itemStyle: { color: '#a0d911' } },
    ]
    if (debtChartRef.value) {
      debtChart = debtChart ?? echarts.init(debtChartRef.value)
      debtChart.setOption(baseOption('偿债能力', debtSeries, ''), true)
    }
  } catch (e) {
    console.error(e)
  } finally {
    indicatorLoading.value = false
  }
}

const loadAnnouncements = async () => {
  annLoading.value = true
  try {
    const res: any = await getAnnouncements({
      stock_code: code.value,
      ann_type: annTypeFilter.value,
      keyword: annKeyword.value || undefined,
      page: annPage.value,
      page_size: annPageSize,
    })
    if (res.data.code === 200) {
      announcements.value = res.data.data.items || []
      annTotal.value = res.data.data.total || 0
    }
  } catch (e) {
    console.error(e)
  } finally {
    annLoading.value = false
  }
}

const loadWatchlist = async () => {
  try {
    const res: any = await getWatchlistGroups()
    if (res.data.code === 200) {
      groups.value = res.data.data.groups || []
      watchlistStocks.value = groups.value.flatMap((g: any) => g.stocks)
    }
  } catch (e) {
    console.error(e)
  }
}

// ========== 工具函数 ==========

const formatMoney = (v: any) => {
  if (!v) return '-'
  const n = Number(v)
  if (n >= 1e8) return (n / 1e8).toFixed(2) + ' 亿'
  if (n >= 1e4) return (n / 1e4).toFixed(2) + ' 万'
  return n.toFixed(2)
}
const formatShare = (v: any) => {
  if (!v) return '-'
  const n = Number(v)
  if (n >= 1e8) return (n / 1e8).toFixed(2) + ' 亿股'
  if (n >= 1e4) return (n / 1e4).toFixed(2) + ' 万股'
  return n.toFixed(0)
}
const formatVolume = (v: any) => {
  if (!v) return '-'
  const n = Number(v)
  if (n >= 1e8) return (n / 1e8).toFixed(2) + ' 亿'
  if (n >= 1e4) return (n / 1e4).toFixed(2) + ' 万'
  return n.toFixed(0)
}
const priceClass = (p: any) => {
  if (!p) return ''
  const n = Number(p)
  return n > 0 ? 'price-up' : n < 0 ? 'price-down' : ''
}

// ========== 公告详情/自选操作 ==========

const showAnnDetail = (item: any) => {
  currentAnn.value = item
  annDetailVisible.value = true
}

const confirmAddWatchlist = async () => {
  let groupName = addForm.value.group_name
  if (!groupName) {
    message.warning('请选择分组')
    return
  }
  if (groupName === '__new__') {
    if (!addForm.value.new_group_name) {
      message.warning('请输入新分组名')
      return
    }
    try {
      await createGroup({ group_name: addForm.value.new_group_name })
      groupName = addForm.value.new_group_name
    } catch {
      message.error('创建分组失败')
      return
    }
  }
  addLoading.value = true
  try {
    await addStock({
      stock_code: code.value,
      stock_name: stockInfo.value.stock_name || code.value,
      group_name: groupName,
    })
    message.success('已加入自选')
    showAddModal.value = false
    loadWatchlist()
  } catch {
    message.error('加入失败')
  } finally {
    addLoading.value = false
  }
}

const quickAddWatchlist = async () => {
  if (groups.value.length === 0) {
    addForm.value.group_name = '__new__'
    addForm.value.new_group_name = '默认分组'
    showAddModal.value = true
    return
  }
  addForm.value.group_name = groups.value[0].group_name
  confirmAddWatchlist()
}
</script>

<style scoped>
.stock-detail {
  display: flex;
  gap: 16px;
  padding: 16px;
  align-items: flex-start;
  min-height: calc(100vh - 64px);
  background: #f0f2f5;
}

.info-panel {
  width: 320px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  position: sticky;
  top: 80px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.info-header .stock-name {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-header .stock-code {
  font-family: 'SF Mono', Consolas, monospace;
  color: #666;
  font-size: 13px;
  margin-top: 4px;
}

.info-actions {
  margin-top: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-item .lbl {
  font-size: 12px;
  color: #999;
}

.info-item .val {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  word-break: break-all;
}

.quote-price {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.quote-price .price {
  font-size: 28px;
  font-weight: 700;
  color: #333;
}

.quote-price .change {
  font-size: 14px;
  font-weight: 500;
}

.quote-date {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.price-up { color: #cf1322; }
.price-down { color: #389e0d; }

.content-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.content-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.toolbar-tip {
  font-size: 12px;
  color: #999;
}

.fin-card {
  margin-bottom: 12px;
}

.indicator-stat-card {
  text-align: center;
}

.indicator-chart {
  height: 320px;
}

.ann-item {
  cursor: pointer;
  transition: background 0.2s;
}

.ann-item:hover {
  background: #fafafa;
}

.ann-title {
  color: #333;
  font-weight: 500;
}

.ann-date {
  font-size: 12px;
  color: #999;
}

/* ===== 东财主要指标 表格 ===== */
.em-main-table {
  border: 1px solid #e8e8e8;
  background: #fff;
  font-size: 12px;
  overflow-x: auto;
}

.em-table-row {
  display: flex;
  border-bottom: 1px solid #f0f0f0;
  min-width: max-content;
}

.em-table-row:hover {
  background: #fafafa;
}

.em-header-row {
  background: #f5f5f5;
  font-weight: 600;
  color: #333;
  position: sticky;
  top: 0;
  z-index: 2;
}

.em-cell {
  padding: 6px 8px;
  border-right: 1px solid #f0f0f0;
  white-space: nowrap;
  min-width: 80px;
  text-align: right;
}

.em-label-cell {
  position: sticky;
  left: 0;
  background: #fff;
  text-align: left;
  font-weight: 500;
  min-width: 200px;
  color: #333;
  border-right: 1px solid #e8e8e8;
  z-index: 1;
}

.em-header-row .em-label-cell {
  background: #f5f5f5;
  z-index: 3;
}

.em-period-cell {
  text-align: center;
  font-weight: 500;
  min-width: 90px;
}

.em-num-cell {
  font-family: 'Consolas', 'Monaco', monospace;
  color: #333;
}

.em-group-row {
  background: #eaf2ff;
  color: #1890ff;
  font-weight: 600;
  padding: 4px 10px;
  font-size: 12px;
  border-bottom: 1px solid #d0e0f0;
}

.em-group-row.alt {
  background: #f0f5ff;
  color: #722ed1;
}

.val-up {
  color: #f5222d;
}

.val-down {
  color: #52c41a;
}
</style>
