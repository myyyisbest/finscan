<template>
  <div class="compare-page">
    <!-- 顶部筛选区 -->
    <a-card class="filter-card">
      <div class="filter-row">
        <div class="filter-item">
          <span class="filter-label">选择分组</span>
          <a-select
            v-model:value="selectedGroupId"
            style="width: 200px"
            @change="onGroupChange"
            placeholder="请选择分组"
            :disabled="!groups.length"
          >
            <a-select-option v-for="g in groups" :key="g.id" :value="g.id">
              {{ g.name }} ({{ g.stock_count || 0 }})
            </a-select-option>
          </a-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">报告期</span>
          <a-select
            v-model:value="selectedReportDate"
            style="width: 180px"
            @change="loadCompareData"
            :disabled="!reportDates.length"
          >
            <a-select-option v-for="r in reportDates" :key="r.report_date" :value="r.report_date">
              {{ r.report_name }}
            </a-select-option>
          </a-select>
        </div>
      </div>

      <!-- 三个对比分类按钮 -->
      <div class="compare-tabs">
        <button
          v-for="tab in compareTabs"
          :key="tab.key"
          class="compare-tab-btn"
          :class="{ active: compareType === tab.key }"
          @click="compareType = tab.key; loadCompareData()"
        >
          <component :is="tab.icon" class="tab-icon" />
          {{ tab.label }}
        </button>
      </div>
    </a-card>

    <!-- 图表区 -->
    <a-spin :spinning="loading">
      <div v-if="compareData.length > 0" class="chart-section fade-in">
        <div class="chart-grid">
          <div v-for="metric in currentMetrics" :key="metric.key" class="chart-card">
            <div class="chart-title">{{ metric.label }}</div>
            <div :ref="el => setChartRef(metric.key, el)" class="compare-chart"></div>
          </div>
        </div>
      </div>

      <!-- 对比表格 -->
      <a-card v-if="compareData.length > 0" class="table-card fade-in">
        <template #title>
          <span>详细指标对比 · {{ currentReportName }}</span>
        </template>
        <a-table
          :columns="tableColumns"
          :data-source="compareData"
          :pagination="false"
          size="middle"
          :scroll="{ x: 900 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'stock_name'">
              <a @click="goToStock(record.stock_code)" class="stock-link">
                {{ record.stock_name }}
              </a>
            </template>
            <template v-else-if="column.key !== 'stock_code'">
              <span v-if="record[column.dataIndex] != null">
                {{ formatValue(record[column.dataIndex], column.dataIndex) }}
              </span>
              <span v-else class="no-data">-</span>
            </template>
          </template>
        </a-table>
      </a-card>

      <a-empty v-if="!loading && compareData.length === 0" description="暂无对比数据">
        <template #description>
          <span>{{ emptyTip }}</span>
        </template>
      </a-empty>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  RiseOutlined, LineChartOutlined, SafetyOutlined, SwapOutlined, FileTextOutlined
} from '@ant-design/icons-vue'
import { watchlistApi, compareApi } from '@/api/finance'
import type { WatchlistItem } from '@/api/finance'

const router = useRouter()

const loading = ref(false)
const groups = ref<{ id: number; name: string; stock_count: number }[]>([])
const selectedGroupId = ref<number | null>(null)
const selectedReportDate = ref('')
const reportDates = ref<{ report_date: string; report_name: string; report_type: string }[]>([])
const compareType = ref('profitability')

const watchlist = ref<WatchlistItem[]>([])
const compareData = ref<any[]>([])
const chartRefs = ref<Record<string, HTMLElement>>({})
const chartInstances = ref<Record<string, echarts.ECharts>>({})

const compareTabs = [
  { key: 'profitability', label: '盈利能力', icon: RiseOutlined },
  { key: 'growth', label: '成长能力', icon: LineChartOutlined },
  { key: 'solvency', label: '偿债能力', icon: SafetyOutlined },
  { key: 'operation', label: '营运能力', icon: SwapOutlined },
  { key: 'financials', label: '关键财务报表项目', icon: FileTextOutlined },
]

const metricConfig: Record<string, { key: string; label: string; unit?: string }[]> = {
  profitability: [
    { key: 'roe', label: 'ROE (%)', unit: '%' },
    { key: 'roa', label: 'ROA (%)', unit: '%' },
    { key: 'gross_margin', label: '毛利率 (%)', unit: '%' },
    { key: 'net_margin', label: '净利率 (%)', unit: '%' },
  ],
  growth: [
    { key: 'revenue_yoy', label: '营收同比 (%)', unit: '%' },
    { key: 'net_profit_yoy', label: '净利润同比 (%)', unit: '%' },
  ],
  solvency: [
    { key: 'debt_ratio', label: '资产负债率 (%)', unit: '%' },
    { key: 'current_ratio', label: '流动比率' },
    { key: 'quick_ratio', label: '速动比率' },
  ],
  operation: [
    { key: 'total_asset_turnover', label: '总资产周转率', unit: '次' },
    { key: 'inventory_turnover', label: '存货周转率', unit: '次' },
    { key: 'receivable_turnover', label: '应收账款周转率', unit: '次' },
  ],
  financials: [
    { key: 'total_revenue', label: '营业总收入', unit: '亿' },
    { key: 'net_profit_parent', label: '归母净利润', unit: '亿' },
    { key: 'total_assets', label: '总资产', unit: '亿' },
    { key: 'total_liabilities', label: '总负债', unit: '亿' },
    { key: 'total_equity', label: '股东权益', unit: '亿' },
    { key: 'operate_cash_net', label: '经营现金流净额', unit: '亿' },
  ],
}

const currentMetrics = computed(() => metricConfig[compareType.value])

const currentReportName = computed(() => {
  const r = reportDates.value.find(x => x.report_date === selectedReportDate.value)
  return r?.report_name || ''
})

const emptyTip = computed(() => {
  if (!groups.value.length) return '请先在"我的自选"中创建分组'
  if (!selectedGroupId.value) return '请选择一个分组开始对比'
  if (!reportDates.value.length) return '该分组暂无财务数据，请先采集'
  return '暂无对比数据'
})

const tableColumns = computed(() => {
  const metrics = currentMetrics.value
  return [
    { title: '股票名称', dataIndex: 'stock_name', key: 'stock_name', width: 120, fixed: 'left' as const },
    { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code', width: 90 },
    ...metrics.map(m => ({
      title: m.label,
      dataIndex: m.key,
      key: m.key,
      width: 110,
      align: 'right' as const,
    })),
  ]
})

function setChartRef(key: string, el: any) {
  if (el) chartRefs.value[key] = el
}

function onGroupChange() {
  if (selectedGroupId.value) {
    loadWatchlist()
  }
}

async function loadGroups() {
  try {
    const res = await watchlistApi.listGroups()
    if (res.code === 0) {
      groups.value = res.data || []
      // 默认选第一个分组
      if (groups.value.length > 0 && !selectedGroupId.value) {
        selectedGroupId.value = groups.value[0].id
        await loadWatchlist()
      }
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadWatchlist() {
  if (!selectedGroupId.value) return
  try {
    const res = await watchlistApi.list(selectedGroupId.value)
    if (res.code === 0) {
      watchlist.value = res.data || []
      await loadReportDates()
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadReportDates() {
  if (watchlist.value.length === 0) {
    reportDates.value = []
    compareData.value = []
    return
  }
  const codes = watchlist.value.map(w => w.stock_code)
  try {
    const res = await compareApi.getReportDates(codes, 20)
    if (res.code === 0) {
      reportDates.value = res.data || []
      if (reportDates.value.length > 0) {
        // 默认选最新年报
        const annual = reportDates.value.find(r => r.report_type === 'Annual')
        selectedReportDate.value = annual?.report_date || reportDates.value[0].report_date
        await loadCompareData()
      }
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadCompareData() {
  if (watchlist.value.length === 0 || !selectedReportDate.value) {
    compareData.value = []
    return
  }

  loading.value = true
  try {
    const codes = watchlist.value.map(w => w.stock_code)
    const res = await compareApi.getReport(codes, selectedReportDate.value)
    if (res.code === 0) {
      compareData.value = res.data?.data || []
      nextTick(() => initCharts())
    }
  } catch (e) {
    console.error('Failed to load compare data:', e)
  } finally {
    loading.value = false
  }
}

function initCharts() {
  const metrics = currentMetrics.value
  const xAxisData = compareData.value.map(d => d.stock_name)

  metrics.forEach(metric => {
    const el = chartRefs.value[metric.key]
    if (!el) return

    if (chartInstances.value[metric.key]) {
      chartInstances.value[metric.key].dispose()
    }

    const chart = echarts.init(el)
    chartInstances.value[metric.key] = chart

    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
    const seriesData = compareData.value.map((d, i) => {
      let val = d[metric.key]
      if (val == null) return { value: null }
      if (metric.unit === '亿') val = val / 1e8
      return {
        value: Number(val),
        itemStyle: { color: colors[i % colors.length] },
      }
    })

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const p = params[0]
          if (p.value == null) return `${p.name}<br/>${metric.label}: -`
          let val = p.value
          if (metric.unit === '亿') val = val.toFixed(2) + ' 亿'
          else if (metric.unit === '%') val = val.toFixed(2) + '%'
          else if (metric.unit === '次') val = val.toFixed(2) + ' 次'
          return `${p.name}<br/>${metric.label}: ${val}`
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: xAxisData,
        axisLabel: { rotate: 20, fontSize: 11, interval: 0 },
      },
      yAxis: {
        type: 'value',
        name: metric.unit || '',
      },
      series: [{
        type: 'bar',
        data: seriesData,
        barWidth: '50%',
        label: {
          show: true,
          position: 'top',
          fontSize: 10,
          formatter: (params: any) => {
            if (params.value == null) return ''
            let val = params.value
            if (metric.unit === '亿') return val.toFixed(1)
            if (metric.unit === '%') return val.toFixed(1) + '%'
            if (metric.unit === '次') return val.toFixed(2)
            return val.toFixed(1)
          }
        }
      }],
    }

    chart.setOption(option)
  })
}

function formatValue(value: any, key: string): string {
  if (value === null || value === undefined) return '-'
  const allMetrics = Object.values(metricConfig).flat()
  const config = allMetrics.find(m => m.key === key)
  if (!config) return String(value)

  let num = Number(value)
  if (config.unit === '亿') return (num / 1e8).toFixed(2) + ' 亿'
  if (config.unit === '%') return num.toFixed(2) + '%'
  if (config.unit === '次') return num.toFixed(2)
  return num.toFixed(2)
}

function goToStock(code: string) {
  router.push(`/stock/${code}/main-indicators`)
}

const handleResize = () => {
  Object.values(chartInstances.value).forEach(c => c.resize())
}

onMounted(async () => {
  await loadGroups()
  window.addEventListener('resize', handleResize)
})

watch(compareType, () => {
  nextTick(() => {
    if (compareData.value.length > 0) {
      initCharts()
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  Object.values(chartInstances.value).forEach(c => c.dispose())
})
</script>

<style scoped>
.compare-page {
  min-height: calc(100vh - 96px);
}

.fade-in { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.filter-card {
  margin-bottom: 16px;
  border-radius: 12px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
  white-space: nowrap;
}

/* 对比分类按钮 */
.compare-tabs {
  display: flex;
  gap: 0;
  background: #f5f5f5;
  border-radius: 10px;
  padding: 4px;
  width: fit-content;
}

.compare-tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  border: none;
  background: transparent;
  color: #666;
  font-size: 13px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.compare-tab-btn:hover {
  color: #1d4ed8;
}
.compare-tab-btn.active {
  background: #fff;
  color: #1d4ed8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.tab-icon {
  font-size: 14px;
}

/* 图表网格 */
.chart-section {
  margin-bottom: 16px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.chart-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e8e8e8;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.compare-chart {
  width: 100%;
  height: 280px;
}

.table-card {
  border-radius: 12px;
}

.stock-link {
  color: #1d4ed8;
  cursor: pointer;
  font-weight: 500;
}
.stock-link:hover {
  text-decoration: underline;
}

.no-data {
  color: #ccc;
}
</style>
