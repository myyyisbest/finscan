<template>
  <div class="stock-detail-page">
    <!-- 左列: 公司基本信息 -->
    <div class="left-panel">
      <div class="company-header">
        <h2 class="company-name">
          {{ stockInfo.stock_name || code }}
          <a-tag v-if="stockInfo.is_st" color="red">ST</a-tag>
        </h2>
        <div class="company-code">{{ code }}</div>
        <a-select
          v-if="watchlistStocks.length > 0"
          v-model:value="selectedGroup"
          placeholder="加入分组"
          style="width: 100%; margin-top: 8px"
          @change="handleAddToWatchlist"
        >
          <a-select-option v-for="g in groups" :key="g.group_name" :value="g.group_name">
            {{ g.group_name }}
          </a-select-option>
        </a-select>
        <a-button v-else type="primary" block style="margin-top: 8px" @click="quickAddWatchlist">
          + 加入自选
        </a-button>
      </div>

      <a-divider />

      <div class="info-grid">
        <div class="info-item">
          <span class="label">所属行业</span>
          <span class="value">{{ stockInfo.industry || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">交易市场</span>
          <span class="value">{{ stockInfo.market || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">市盈率(PE)</span>
          <span class="value">{{ overviewData.pe || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">市净率(PB)</span>
          <span class="value">{{ overviewData.pb || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">总市值</span>
          <span class="value">{{ formatMoney(overviewData.total_market_cap) }}</span>
        </div>
        <div class="info-item">
          <span class="label">流通市值</span>
          <span class="value">{{ formatMoney(overviewData.float_market_cap) }}</span>
        </div>
        <div class="info-item">
          <span class="label">ROE</span>
          <span class="value">{{ overviewData.roe ? overviewData.roe + '%' : '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">毛利率</span>
          <span class="value">{{ overviewData.gross_margin ? overviewData.gross_margin + '%' : '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">净利润率</span>
          <span class="value">{{ overviewData.net_margin ? overviewData.net_margin + '%' : '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">营收增长率</span>
          <span class="value" :class="growthClass(overviewData.revenue_growth)">
            {{ overviewData.revenue_growth ? overviewData.revenue_growth + '%' : '-' }}
          </span>
        </div>
        <div class="info-item">
          <span class="label">净利润增长率</span>
          <span class="value" :class="growthClass(overviewData.profit_growth)">
            {{ overviewData.profit_growth ? overviewData.profit_growth + '%' : '-' }}
          </span>
        </div>
        <div class="info-item">
          <span class="label">资产负债率</span>
          <span class="value">{{ overviewData.debt_ratio ? overviewData.debt_ratio + '%' : '-' }}</span>
        </div>
      </div>
    </div>

    <!-- 右列: Tab 区域 -->
    <div class="right-panel">
      <a-tabs v-model:activeKey="activeTab" class="finance-tabs">
        <!-- 财务分析 -->
        <a-tab-pane key="financial" tab="财务分析">
          <div class="tab-toolbar">
            <a-radio-group v-model:value="finPeriod" button-style="solid" size="small">
              <a-radio-button value="annual">年度报告</a-radio-button>
              <a-radio-button value="quarter">季度报告</a-radio-button>
            </a-radio-group>
            <a-radio-group v-model:value="finYear" size="small">
              <a-radio-button v-for="y in availableYears" :key="y" :value="y">{{ y }}</a-radio-button>
            </a-radio-group>
          </div>

          <a-spin :spinning="finLoading">
            <!-- 利润表 -->
            <a-card title="利润表" size="small" class="statement-card">
              <a-table
                :columns="finColumns"
                :data-source="incomeData"
                :pagination="false"
                size="small"
                bordered
              >
                <template #bodyCell="{ column, record }">
                  <span :class="{ negative: record.value < 0 }">{{ record.value }}</span>
                </template>
              </a-table>
            </a-card>

            <!-- 资产负债表 -->
            <a-card title="资产负债表" size="small" class="statement-card">
              <a-table
                :columns="finColumns"
                :data-source="balanceData"
                :pagination="false"
                size="small"
                bordered
              >
                <template #bodyCell="{ column, record }">
                  <span :class="{ negative: record.value < 0 }">{{ record.value }}</span>
                </template>
              </a-table>
            </a-card>

            <!-- 现金流量表 -->
            <a-card title="现金流量表" size="small" class="statement-card">
              <a-table
                :columns="finColumns"
                :data-source="cashflowData"
                :pagination="false"
                size="small"
                bordered
              >
                <template #bodyCell="{ column, record }">
                  <span :class="{ negative: record.value < 0 }">{{ record.value }}</span>
                </template>
              </a-table>
            </a-card>
          </a-spin>
        </a-tab-pane>

        <!-- 指标趋势 -->
        <a-tab-pane key="indicators" tab="指标趋势">
          <a-spin :spinning="indicatorLoading">
            <div ref="indicatorChartRef" class="indicator-chart"></div>
            <a-row :gutter="12" class="indicator-grid">
              <a-col :span="8" v-for="item in indicatorCards" :key="item.key">
                <a-card size="small" class="indicator-card">
                  <a-statistic
                    :title="item.label"
                    :value="item.value"
                    :precision="2"
                    :value-style="{ color: item.color }"
                  />
                </a-card>
              </a-col>
            </a-row>
          </a-spin>
        </a-tab-pane>

        <!-- 公告信息 -->
        <a-tab-pane key="announcement" tab="公告信息">
          <a-spin :spinning="annLoading">
            <a-list
              size="small"
              :data-source="announcements"
              :loading="annLoading"
              class="ann-list"
            >
              <template #renderItem="{ item }">
                <a-list-item class="ann-list-item">
                  <a-list-item-meta>
                    <template #title>
                      <a @click="showAnnDetail(item)">{{ item.ann_title }}</a>
                    </template>
                    <template #description>
                      <a-space>
                        <a-tag :color="getAnnTypeColor(item.ann_type)">{{ item.ann_type }}</a-tag>
                        <span>{{ item.publish_date }}</span>
                      </a-space>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
            <a-empty v-if="!annLoading && announcements.length === 0" description="暂无公告" />
          </a-spin>
        </a-tab-pane>
      </a-tabs>
    </div>

    <!-- 公告详情弹窗 -->
    <a-modal
      v-model:open="annDetailVisible"
      :title="currentAnn?.ann_title"
      width="800px"
      :footer="null"
    >
      <div v-if="currentAnn">
        <a-descriptions size="small" :column="2" style="margin-bottom: 16px">
          <a-descriptions-item label="股票代码">{{ currentAnn.stock_code }}</a-descriptions-item>
          <a-descriptions-item label="公告类型">{{ currentAnn.ann_type }}</a-descriptions-item>
          <a-descriptions-item label="发布日期">{{ currentAnn.publish_date }}</a-descriptions-item>
        </a-descriptions>
        <a-divider />
        <div class="ann-content">{{ currentAnn.content_summary || '暂无摘要' }}</div>
        <div v-if="currentAnn.pdf_url" style="margin-top: 16px">
          <a :href="currentAnn.pdf_url" target="_blank">查看原文PDF</a>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { message } from 'ant-design-vue'
import { getStockOverview, getBalanceSheet, getIncomeStatement, getCashFlow } from '@/api/stock'
import { getAnnouncements } from '@/api/announcement'
import { getWatchlistGroups, addToWatchlist as addStock } from '@/api/watchlist'

const route = useRoute()
const code = computed(() => route.params.code as string)

const activeTab = ref('financial')
const finPeriod = ref('annual')
const finYear = ref('')
const finLoading = ref(false)
const indicatorLoading = ref(false)
const annLoading = ref(false)

const stockInfo = ref<any>({})
const overviewData = ref<any>({})
const groups = ref<any[]>([])
const watchlistStocks = ref<any[]>([])
const selectedGroup = ref<string | undefined>()

const incomeData = ref<any[]>([])
const balanceData = ref<any[]>([])
const cashflowData = ref<any[]>([])
const announcements = ref<any[]>([])
const annDetailVisible = ref(false)
const currentAnn = ref<any>(null)

const indicatorChartRef = ref<HTMLElement | null>(null)
let indicatorChart: echarts.ECharts | null = null

const availableYears = computed(() => {
  if (finPeriod.value === 'annual') {
    return ['2024', '2023', '2022', '2021', '2020']
  }
  return ['2024Q3', '2024Q2', '2024Q1', '2023Q4', '2023Q3']
})

const finColumns = [
  { title: '指标', dataIndex: 'label', width: 200, fixed: 'left' },
]

const indicatorCards = computed(() => [
  { key: 'pe', label: '市盈率(PE)', value: overviewData.value.pe || 0, color: '#1890ff' },
  { key: 'pb', label: '市净率(PB)', value: overviewData.value.pb || 0, color: '#722ED1' },
  { key: 'roe', label: '净资产收益率(%)', value: overviewData.value.roe || 0, color: '#13C2C2' },
  { key: 'gross_margin', label: '毛利率(%)', value: overviewData.value.gross_margin || 0, color: '#F5222D' },
  { key: 'net_margin', label: '净利润率(%)', value: overviewData.value.net_margin || 0, color: '#FA541C' },
  { key: 'revenue_growth', label: '营收增长率(%)', value: overviewData.value.revenue_growth || 0, color: '#52C41A' },
])

watch([finPeriod, finYear], () => {
  if (activeTab.value === 'financial') loadFinancial()
})

watch(finPeriod, () => {
  // reset year when period changes
  finYear.value = ''
})

watch(activeTab, (tab) => {
  if (tab === 'financial') loadFinancial()
  else if (tab === 'indicators') loadIndicators()
  else if (tab === 'announcement') loadAnnouncements()
})

const loadOverview = async () => {
  try {
    const res = await getStockOverview(code.value)
    if (res.data.code === 200) {
      overviewData.value = res.data.data.latest_annual || {}
      stockInfo.value = res.data.data.basic || {}
    }
  } catch (e) {
    console.error(e)
  }
}

const loadFinancial = async () => {
  if (!finYear.value) finYear.value = availableYears.value[0]
  finLoading.value = true
  try {
    const period = finPeriod.value === 'annual' ? 'Annual' : finYear.value
    const [balanceRes, incomeRes, cashflowRes] = await Promise.all([
      getBalanceSheet(code.value, { report_type: period }),
      getIncomeStatement(code.value, { report_type: period }),
      getCashFlow(code.value, { report_type: period }),
    ])

    const buildTableData = (res: any, fields: string[]) => {
      if (res.data.code !== 200 || !res.data.data.items?.length) return []
      const row = res.data.data.items[0]
      return fields.map(f => ({ label: f, value: row[f] ?? '-' }))
    }

    const balanceFields = [
      'total_assets', 'total_current_assets', 'monetary_funds',
      'accounts_receivable', 'inventory', 'total_liabilities',
      'total_equity', 'share_capital', 'retained_profits'
    ]
    const incomeFields = [
      'total_revenue', 'operating_cost', 'gross_profit',
      'operating_profit', 'total_profit', 'net_profit',
      'net_profit_parent', 'gross_margin', 'net_margin'
    ]
    const cashflowFields = [
      'operating_cash_inflow', 'operating_cash_outflow', 'operating_cash_net',
      'investing_cash_net', 'financing_cash_net', 'free_cash_flow'
    ]

    balanceData.value = buildTableData(balanceRes, balanceFields)
    incomeData.value = buildTableData(incomeRes, incomeFields)
    cashflowData.value = buildTableData(cashflowRes, cashflowFields)

    // dynamic columns based on selected period
    const periods = [finPeriod.value === 'annual' ? finYear.value + '年报' : finYear.value]
    finColumns.length = 0
    finColumns.push({ title: '指标', dataIndex: 'label', width: 180, fixed: 'left' as const })
    periods.forEach(p => finColumns.push({ title: p, dataIndex: 'value' }))
  } catch (e) {
    console.error(e)
  } finally {
    finLoading.value = false
  }
}


const loadIndicators = async () => {
  indicatorLoading.value = true
  await loadOverview()
  setTimeout(() => {
    if (indicatorChartRef.value) {
      if (!indicatorChart) indicatorChart = echarts.init(indicatorChartRef.value)
      indicatorChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['PE', 'PB', 'ROE'] },
        xAxis: { type: 'category', data: ['2020', '2021', '2022', '2023', '2024'] },
        yAxis: [
          { type: 'value', name: 'PE/PB', position: 'left' },
          { type: 'value', name: 'ROE%', position: 'right' }
        ],
        series: [
          { name: 'PE', type: 'line', data: [overviewData.value.pe || 0, 0, 0, 0, 0] },
          { name: 'PB', type: 'line', data: [overviewData.value.pb || 0, 0, 0, 0, 0] },
          { name: 'ROE', type: 'line', yAxisIndex: 1, data: [overviewData.value.roe || 0, 0, 0, 0, 0] }
        ]
      })
    }
    indicatorLoading.value = false
  }, 300)
}

const loadAnnouncements = async () => {
  annLoading.value = true
  try {
    const res = await getAnnouncements({ stock_code: code.value, page: 1, page_size: 20 })
    if (res.data.code === 200) {
      announcements.value = res.data.data.items || []
    }
  } catch (e) {
    console.error(e)
  } finally {
    annLoading.value = false
  }
}

const loadWatchlist = async () => {
  try {
    const res = await getWatchlistGroups()
    if (res.data.code === 200) {
      groups.value = res.data.data.groups || []
      watchlistStocks.value = groups.value.flatMap((g: any) => g.stocks)
    }
  } catch (e) {
    console.error(e)
  }
}

const handleAddToWatchlist = async (groupName: string) => {
  try {
    await addStock({ stock_code: code.value, stock_name: stockInfo.value.stock_name || code.value, group_name: groupName })
    message.success('已加入自选')
    loadWatchlist()
  } catch {
    message.error('加入失败')
  }
}

const quickAddWatchlist = async () => {
  const group = groups.value[0]?.group_name || '默认分组'
  await handleAddToWatchlist(group)
}

const showAnnDetail = (item: any) => {
  currentAnn.value = item
  annDetailVisible.value = true
}

const formatMoney = (val: number | string | null) => {
  if (!val) return '-'
  if (typeof val === 'string') return val
  if (val >= 1e8) return (val / 1e8).toFixed(2) + '亿'
  if (val >= 1e4) return (val / 1e4).toFixed(2) + '万'
  return val.toFixed(2)
}

const growthClass = (v: number) => v > 0 ? 'growth-up' : v < 0 ? 'growth-down' : ''

const getAnnTypeColor = (type: string) => {
  if (type?.includes('年报') || type?.includes('半年报')) return 'blue'
  if (type?.includes('季报')) return 'cyan'
  if (type?.includes('发行') || type?.includes('上市')) return 'purple'
  return 'default'
}

onMounted(async () => {
  await loadOverview()
  await loadWatchlist()
  await loadFinancial()
})

onActivated(() => {
  if (route.params.code !== code.value) {
    window.location.reload()
  }
})
</script>

<style scoped>
.stock-detail-page {
  display: flex;
  gap: 16px;
  padding: 16px;
  min-height: calc(100vh - 64px);
}

.left-panel {
  width: 280px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  height: fit-content;
  position: sticky;
  top: 80px;
}

.company-name {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.company-code {
  font-family: 'SF Mono', Consolas, monospace;
  color: #666;
  font-size: 13px;
  margin-top: 4px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.label {
  font-size: 12px;
  color: #999;
}

.value {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.right-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.finance-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 12px;
}

.tab-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.statement-card {
  margin-bottom: 16px;
}

.indicator-chart {
  height: 280px;
  margin-bottom: 16px;
}

.indicator-grid {
  margin-top: 12px;
}

.indicator-card {
  text-align: center;
}

.ann-list {
  max-height: 600px;
  overflow-y: auto;
}

.ann-list-item {
  cursor: pointer;
}

.ann-list-item:hover {
  background: #f5f5f5;
}

.ann-content {
  line-height: 1.8;
  color: #333;
  white-space: pre-wrap;
}

.growth-up {
  color: #cf1322;
}

.growth-down {
  color: #389e0d;
}

.negative {
  color: #cf1322;
}
</style>
