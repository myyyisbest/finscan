<template>
  <div class="compare-page">
    <a-card title="股票对比分析" class="compare-card">
      <template #extra>
        <a-space>
          <a-select
            v-model:value="compareType"
            style="width: 150px"
            @change="loadCompareData"
          >
            <a-select-option value="profitability">盈利能力</a-select-option>
            <a-select-option value="efficiency">运营效率</a-select-option>
            <a-select-option value="structure">资本结构</a-select-option>
            <a-select-option value="scale">规模对比</a-select-option>
          </a-select>
          <a-button @click="showStockPicker = true">添加股票</a-button>
        </a-space>
      </template>

      <a-spin :spinning="loading">
        <div class="chart-section">
          <div ref="chartRef" class="compare-chart"></div>
        </div>

        <a-table
          :columns="tableColumns"
          :data-source="compareData"
          :pagination="false"
          class="compare-table"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'stock_name'">
              <a @click="goToStock(record.stock_code)">{{ record.stock_name }}</a>
            </template>
            <template v-else-if="column.key === 'value'">
              <span class="mono-number">{{ formatValue(record.value, column.dataIndex as string) }}</span>
            </template>
          </template>
        </a-table>
      </a-spin>
    </a-card>

    <a-modal
      v-model:open="showStockPicker"
      title="选择股票"
      @ok="handleAddStock"
    >
      <GlobalSearch @select="handleStockSelect" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import GlobalSearch from '@/components/GlobalSearch.vue'
import { getStockOverview, getIndicators } from '@/api/stock'
import type { StockSearchItem } from '@/types'

const router = useRouter()
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const loading = ref(false)
const showStockPicker = ref(false)
const compareType = ref('profitability')
const selectedStocks = ref<StockSearchItem[]>([])
const compareData = ref<any[]>([])

const metricConfig: Record<string, { key: string; label: string; unit?: string }[]> = {
  profitability: [
    { key: 'roe', label: 'ROE', unit: '%' },
    { key: 'roa', label: 'ROA', unit: '%' },
    { key: 'gross_margin', label: '毛利率', unit: '%' },
    { key: 'net_margin', label: '净利率', unit: '%' }
  ],
  efficiency: [
    { key: 'inventory_turnover', label: '存货周转率', unit: '' },
    { key: 'total_asset_turnover', label: '总资产周转率', unit: '' }
  ],
  structure: [
    { key: 'debt_to_assets', label: '资产负债率', unit: '%' },
    { key: 'current_ratio', label: '流动比率', unit: '' },
    { key: 'quick_ratio', label: '速动比率', unit: '' }
  ],
  scale: [
    { key: 'revenue', label: '营收', unit: '亿' },
    { key: 'net_profit', label: '净利润', unit: '亿' },
    { key: 'total_assets', label: '总资产', unit: '亿' },
    { key: 'equity', label: '所有者权益', unit: '亿' }
  ]
}

const tableColumns = computed(() => {
  const metrics = metricConfig[compareType.value]
  return [
    { title: '股票', dataIndex: 'stock_name', key: 'stock_name' },
    { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code' },
    ...metrics.map(m => ({ title: m.label, dataIndex: m.key, key: m.key }))
  ]
})

const handleStockSelect = (stockCode: string) => {
  if (!selectedStocks.value.find(s => s.stock_code === stockCode)) {
    selectedStocks.value.push({
      stock_code: stockCode,
      stock_name: stockCode,
      is_st: false,
      industry: null,
      market: null
    })
  }
}

const handleAddStock = () => {
  showStockPicker.value = false
  loadCompareData()
}

const loadCompareData = async () => {
  if (selectedStocks.value.length === 0) return

  loading.value = true
  compareData.value = []

  try {
    const results = await Promise.all(
      selectedStocks.value.map(async (stock) => {
        const overviewRes = await getStockOverview(stock.stock_code)
        const indicatorsRes = await getIndicators(stock.stock_code, { page: 1, page_size: 1 })

        // axios interceptor already unwraps response.data, so we access directly
        const overview = overviewRes.code === 0 ? overviewRes.data : null
        const indicator = indicatorsRes.code === 0 && indicatorsRes.data.items.length > 0
          ? indicatorsRes.data.items[0]
          : null

        return {
          stock_code: stock.stock_code,
          stock_name: overview?.basic?.stock_name || stock.stock_code,
          ...(overview?.latest_annual || {}),
          ...(indicator || {})
        }
      })
    )

    compareData.value = results
    nextTick(() => initChart())
  } catch (error) {
    console.error('Failed to load compare data:', error)
  } finally {
    loading.value = false
  }
}

const initChart = () => {
  if (!chartRef.value || compareData.value.length === 0) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  const metrics = metricConfig[compareType.value]
  const xAxisData = compareData.value.map(d => d.stock_name || d.stock_code)
  const series = metrics.map(m => ({
    name: m.label,
    type: 'bar',
    data: compareData.value.map(d => {
      const val = d[m.key]
      if (val === null || val === undefined) return null
      if (compareType.value === 'scale') {
        return (val / 1e8).toFixed(2)
      }
      return val
    })
  }))

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: {
      bottom: 10
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xAxisData
    },
    yAxis: {
      type: 'value'
    },
    series: series as any
  }

  chartInstance.setOption(option)
}

const formatValue = (value: any, key: string): string => {
  if (value === null || value === undefined) return '-'
  const config = metricConfig[compareType.value].find(m => m.key === key)
  if (!config) return String(value)

  if (compareType.value === 'scale' && config.unit === '亿') {
    return value.toFixed(2) + ' 亿'
  }
  return value.toFixed(2) + (config.unit || '')
}

const goToStock = (code: string) => {
  router.push(`/stock/${code}`)
}

const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.compare-page {
  padding: 16px;
}

.compare-card {
  min-height: 500px;
}

.chart-section {
  margin-bottom: 24px;
}

.compare-chart {
  width: 100%;
  height: 400px;
}
</style>
