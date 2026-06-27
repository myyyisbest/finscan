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
          >
            <a-select-option :value="0">全部公司</a-select-option>
            <a-select-option v-for="g in groups" :key="g.id" :value="g.id">
              {{ g.name }}
            </a-select-option>
          </a-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">报告期间</span>
          <a-select v-model:value="reportType" style="width: 160px" @change="loadCompareData">
            <a-select-option value="Annual">年报</a-select-option>
            <a-select-option value="Q3">三季报</a-select-option>
            <a-select-option value="H1">半年报</a-select-option>
            <a-select-option value="Q1">一季报</a-select-option>
          </a-select>
        </div>
      </div>

      <!-- 四个对比分类按钮 -->
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
          <span>详细指标对比</span>
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
          <span>请选择分组并确保股票已采集财务数据</span>
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
  RiseOutlined, SwapOutlined, AppstoreOutlined, BarChartOutlined
} from '@ant-design/icons-vue'
import { watchlistApi } from '@/api/finance'
import type { WatchlistItem } from '@/api/finance'

const router = useRouter()

const loading = ref(false)
const groups = ref<{ id: number; name: string; stock_count: number }[]>([])
const selectedGroupId = ref<number>(0)
const reportType = ref('Annual')
const compareType = ref('profitability')

const watchlist = ref<WatchlistItem[]>([])
const compareData = ref<any[]>([])
const chartRefs = ref<Record<string, HTMLElement>>({})
const chartInstances = ref<Record<string, echarts.ECharts>>({})

const compareTabs = [
  { key: 'profitability', label: '盈利能力', icon: RiseOutlined },
  { key: 'efficiency', label: '运营效率', icon: SwapOutlined },
  { key: 'structure', label: '资本结构', icon: AppstoreOutlined },
  { key: 'scale', label: '规模对比', icon: BarChartOutlined },
]

const metricConfig: Record<string, { key: string; label: string; unit?: string }[]> = {
  profitability: [
    { key: 'roe', label: 'ROE (%)', unit: '%' },
    { key: 'roa', label: 'ROA (%)', unit: '%' },
    { key: 'gross_margin', label: '毛利率 (%)', unit: '%' },
    { key: 'net_margin', label: '净利率 (%)', unit: '%' },
  ],
  efficiency: [
    { key: 'total_asset_turnover', label: '总资产周转率', unit: '次' },
  ],
  structure: [
    { key: 'debt_to_assets', label: '资产负债率 (%)', unit: '%' },
    { key: 'current_ratio', label: '流动比率' },
    { key: 'quick_ratio', label: '速动比率' },
  ],
  scale: [
    { key: 'total_revenue', label: '营业总收入', unit: '亿' },
    { key: 'net_profit_parent', label: '归母净利润', unit: '亿' },
    { key: 'total_assets', label: '总资产', unit: '亿' },
    { key: 'total_equity', label: '所有者权益', unit: '亿' },
  ],
}

const currentMetrics = computed(() => metricConfig[compareType.value])

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
  loadWatchlist()
}

async function loadGroups() {
  try {
    const res = await watchlistApi.listGroups()
    if (res.code === 0) {
      groups.value = res.data || []
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadWatchlist() {
  try {
    const res = await watchlistApi.list(
      selectedGroupId.value === 0 ? undefined : selectedGroupId.value
    )
    if (res.code === 0) {
      watchlist.value = res.data || []
      await loadCompareData()
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadCompareData() {
  if (watchlist.value.length === 0) {
    compareData.value = []
    return
  }

  loading.value = true
  try {
    // 从最新报告数据中提取指标
    const data = watchlist.value.map(item => {
      const report = item.latest_report
      return {
        stock_code: item.stock_code,
        stock_name: item.stock_name,
        total_revenue: report?.total_revenue,
        net_profit_parent: report?.net_profit_parent,
        total_assets: report?.total_assets,
        total_equity: report?.total_equity,
        roe: report?.roe,
        roa: report?.roa,
        gross_margin: report?.gross_margin,
        net_margin: report?.net_margin,
        debt_to_assets: report?.debt_ratio,
        current_ratio: report?.current_ratio,
        quick_ratio: report?.quick_ratio,
        total_asset_turnover: report?.total_asset_turnover,
      }
    })
    compareData.value = data
    nextTick(() => initCharts())
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
  await loadWatchlist()
  window.addEventListener('resize', handleResize)
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

/* 四个对比分类按钮 */
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
