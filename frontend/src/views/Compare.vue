<template>
  <div class="compare-page">
    <a-card title="公司财务对比" class="compare-card">
      <template #extra>
        <a-space>
          <span class="hint">最多对比 4 家</span>
          <GlobalSearch no-navigate @select="handleAddStock" />
          <a-button @click="resetCompare">重置</a-button>
        </a-space>
      </template>

      <a-spin :spinning="loading">
        <a-row :gutter="16" v-if="selectedStocks.length > 0" style="margin-bottom: 12px">
          <a-col :span="24">
            <div class="selected-stocks">
              <a-tag
                v-for="s in selectedStocks"
                :key="s.stock_code"
                closable
                @close="removeStock(s.stock_code)"
                color="blue"
                class="stock-tag"
              >
                {{ s.stock_name }} ({{ s.stock_code }})
              </a-tag>
            </div>
          </a-col>
        </a-row>

        <a-empty v-if="selectedStocks.length === 0" description="请添加股票进行对比">
          <template #image>
            <BarChartOutlined style="font-size: 48px; color: #ccc" />
          </template>
        </a-empty>

        <template v-else>
          <!-- 实时行情对比卡 -->
          <a-row :gutter="12" style="margin-bottom: 16px">
            <a-col v-for="s in selectedStocks" :key="s.stock_code" :span="24 / Math.max(selectedStocks.length, 1)">
              <a-card size="small" class="quote-card" hoverable @click="$router.push(`/stock/${s.stock_code}`)">
                <div class="quote-name">{{ s.stock_name }}</div>
                <div class="quote-price" :class="priceClass(quoteMap[s.stock_code]?.change_pct)">
                  {{ quoteMap[s.stock_code]?.latest_price || '-' }}
                  <span class="quote-change">
                    {{ Number(quoteMap[s.stock_code]?.change_amount || 0) >= 0 ? '+' : '' }}{{ quoteMap[s.stock_code]?.change_amount || '0' }}
                    ({{ Number(quoteMap[s.stock_code]?.change_pct || 0) >= 0 ? '+' : '' }}{{ quoteMap[s.stock_code]?.change_pct || '0' }}%)
                  </span>
                </div>
                <div class="quote-meta">
                  市值 {{ formatMoney(quoteMap[s.stock_code]?.total_market_cap) }} · PE {{ quoteMap[s.stock_code]?.pe || '-' }} · PB {{ quoteMap[s.stock_code]?.pb || '-' }}
                </div>
              </a-card>
            </a-col>
          </a-row>

          <!-- 财务对比表 -->
          <a-card size="small" title="财务指标对比" class="compare-card-inner">
            <a-table
              :columns="compareColumns"
              :data-source="compareData"
              :pagination="false"
              bordered
              size="small"
              row-key="key"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key !== 'indicator'">
                  <span :class="getCompareClass(record, column.key)">
                    {{ record[column.key] }}
                  </span>
                </template>
                <template v-else>
                  <b>{{ record.indicator }}</b>
                </template>
              </template>
            </a-table>
          </a-card>

          <!-- 对比图 -->
          <a-row :gutter="12" style="margin-top: 12px">
            <a-col :span="12">
              <a-card size="small" title="盈利能力对比">
                <div ref="profitChartRef" class="compare-chart"></div>
              </a-card>
            </a-col>
            <a-col :span="12">
              <a-card size="small" title="规模对比 (营收/净利)">
                <div ref="sizeChartRef" class="compare-chart"></div>
              </a-card>
            </a-col>
          </a-row>
        </template>
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { BarChartOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'
import GlobalSearch from '@/components/GlobalSearch.vue'
import { getStockOverview, getBatchQuote } from '@/api/stock'

const loading = ref(false)
const selectedStocks = ref<any[]>([])
const overviewMap = ref<Record<string, any>>({})
const quoteMap = ref<Record<string, any>>({})

const profitChartRef = ref<HTMLElement | null>(null)
const sizeChartRef = ref<HTMLElement | null>(null)
let profitChart: echarts.ECharts | null = null
let sizeChart: echarts.ECharts | null = null

const indicators = [
  { key: 'latest_price', label: '最新价', fmt: 'price' },
  { key: 'change_pct', label: '涨跌幅(%)', fmt: 'num' },
  { key: 'pe', label: 'PE(动)', fmt: 'num' },
  { key: 'pb', label: 'PB', fmt: 'num' },
  { key: 'total_market_cap', label: '总市值(亿)', fmt: 'money' },
  { key: 'float_market_cap', label: '流通市值(亿)', fmt: 'money' },
  { key: 'roe', label: 'ROE(%)', fmt: 'num' },
  { key: 'gross_margin', label: '毛利率(%)', fmt: 'num' },
  { key: 'net_margin', label: '净利率(%)', fmt: 'num' },
  { key: 'revenue_yoy', label: '营收同比(%)', fmt: 'num' },
  { key: 'net_profit_yoy', label: '净利同比(%)', fmt: 'num' },
  { key: 'debt_to_assets', label: '资产负债率(%)', fmt: 'num' },
  { key: 'current_ratio', label: '流动比率', fmt: 'num' },
  { key: 'total_revenue', label: '营业总收入(亿)', fmt: 'bigMoney' },
  { key: 'net_profit_parent', label: '归母净利润(亿)', fmt: 'bigMoney' },
  { key: 'total_assets', label: '总资产(亿)', fmt: 'bigMoney' },
  { key: 'total_equity', label: '净资产(亿)', fmt: 'bigMoney' },
]

const compareData = ref<any[]>([])

const compareColumns = computed(() => {
  const cols: any[] = [{ title: '指标', key: 'indicator', fixed: 'left', width: 160 }]
  selectedStocks.value.forEach(s => {
    cols.push({ title: `${s.stock_name} (${s.stock_code})`, key: s.stock_code, width: 180 })
  })
  return cols
})

const handleAddStock = async (item: { stock_code: string; stock_name: string }) => {
  if (selectedStocks.value.find(s => s.stock_code === item.stock_code)) {
    message.warning('已添加该股票')
    return
  }
  if (selectedStocks.value.length >= 4) {
    message.warning('最多对比 4 家公司')
    return
  }
  selectedStocks.value.push(item)
  await loadCompare()
}

const removeStock = async (code: string) => {
  selectedStocks.value = selectedStocks.value.filter(s => s.stock_code !== code)
  await loadCompare()
}

const resetCompare = () => {
  selectedStocks.value = []
  compareData.value = []
  overviewMap.value = {}
  quoteMap.value = {}
}

const formatMoney = (v: any) => {
  if (!v) return '-'
  const n = Number(v)
  if (n >= 1e8) return (n / 1e8).toFixed(2)
  if (n >= 1e4) return (n / 1e4).toFixed(2)
  return n.toFixed(2)
}

const formatValue = (v: any, fmt: string) => {
  if (v == null || v === '') return '-'
  const n = Number(v)
  if (isNaN(n)) return String(v)
  if (fmt === 'num' || fmt === 'price') return n.toFixed(2)
  if (fmt === 'money') return (n / 1e8).toFixed(2)
  if (fmt === 'bigMoney') return (n / 1e8).toFixed(2)
  return String(v)
}

const loadCompare = async () => {
  if (selectedStocks.value.length === 0) {
    compareData.value = []
    return
  }
  loading.value = true
  try {
    const codes = selectedStocks.value.map(s => s.stock_code)
    // 行情（批量）
    const qRes = await getBatchQuote(codes)
    if (qRes.data.code === 200) {
      quoteMap.value = {}
      ;(qRes.data.data || []).forEach((q: any) => {
        quoteMap.value[q.stock_code] = q
      })
    }
    // 财务（overview）
    const allOverviews = await Promise.all(codes.map(c => getStockOverview(c)))
    const oMap: Record<string, any> = {}
    allOverviews.forEach((res: any, i) => {
      if (res.data.code === 200) oMap[codes[i]] = res.data.data
    })
    overviewMap.value = oMap

    compareData.value = indicators.map(ind => {
      const row: any = { indicator: ind.label, key: ind.key }
      selectedStocks.value.forEach(s => {
        const code = s.stock_code
        const quote = quoteMap.value[code] || {}
        const ov = oMap[code] || {}
        const ann = ov.latest_annual || {}
        // 优先取行情字段, 否则从 overview
        let val: any
        if (['latest_price', 'change_pct', 'pe', 'pb', 'total_market_cap', 'float_market_cap'].includes(ind.key)) {
          val = quote[ind.key === 'pe' ? 'pe' : ind.key === 'pb' ? 'pb' : ind.key]
        } else {
          val = ann[ind.key]
        }
        row[code] = formatValue(val, ind.fmt)
        row[`${code}_raw`] = Number(val) || 0
      })
      return row
    })

    await nextTick()
    renderCharts()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  const names = selectedStocks.value.map(s => s.stock_name)
  const codes = selectedStocks.value.map(s => s.stock_code)
  const colors = ['#1890ff', '#52c41a', '#fa8c16', '#722ed1']

  // 盈利对比
  if (profitChartRef.value) {
    profitChart = profitChart ?? echarts.init(profitChartRef.value)
    profitChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: names, top: 0 },
      grid: { left: 50, right: 30, bottom: 30, top: 30 },
      xAxis: { type: 'category', data: names },
      yAxis: { type: 'value', name: '%' },
      series: [
        {
          name: 'ROE(%)',
          type: 'bar',
          data: codes.map((c, i) => ({ value: Number(overviewMap.value[c]?.latest_annual?.roe || 0), itemStyle: { color: colors[i] } })),
        },
        {
          name: '净利率(%)',
          type: 'bar',
          data: codes.map((c, i) => ({ value: Number(overviewMap.value[c]?.latest_annual?.net_margin || 0), itemStyle: { color: colors[i], opacity: 0.5 } })),
        },
      ],
    }, true)
  }
  // 规模对比
  if (sizeChartRef.value) {
    sizeChart = sizeChart ?? echarts.init(sizeChartRef.value)
    sizeChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['营业总收入', '归母净利润'], top: 0 },
      grid: { left: 60, right: 30, bottom: 30, top: 30 },
      xAxis: { type: 'category', data: names },
      yAxis: { type: 'value', name: '亿' },
      series: [
        {
          name: '营业总收入',
          type: 'bar',
          data: codes.map((c, i) => ({ value: Number(overviewMap.value[c]?.latest_annual?.total_revenue || 0) / 1e8, itemStyle: { color: colors[i] } })),
        },
        {
          name: '归母净利润',
          type: 'bar',
          data: codes.map((c, i) => ({ value: Number(overviewMap.value[c]?.latest_annual?.net_profit_parent || 0) / 1e8, itemStyle: { color: colors[i], opacity: 0.5 } })),
        },
      ],
    }, true)
  }
}

const getCompareClass = (record: any, code: string) => {
  const rawKey = `${code}_raw`
  const val = record[rawKey]
  if (!val) return ''
  const values = selectedStocks.value
    .map(s => record[`${s.stock_code}_raw`])
    .filter((v: any) => v != null && v !== 0)
  if (values.length === 0) return ''
  const max = Math.max(...(values as number[]))
  const min = Math.min(...(values as number[]))
  // 越低越好: 资产负债率
  const lowerBetter = record.indicator.includes('资产负债率')
  if (lowerBetter) {
    if (val === min) return 'cell-best'
    if (val === max) return 'cell-worst'
  } else {
    if (val === max) return 'cell-best'
    if (val === min) return 'cell-worst'
  }
  return ''
}

const priceClass = (p: any) => {
  const n = Number(p || 0)
  return n > 0 ? 'price-up' : n < 0 ? 'price-down' : ''
}

onMounted(() => {})
onBeforeUnmount(() => {
  profitChart?.dispose()
  sizeChart?.dispose()
})
</script>

<style scoped>
.compare-page {
  padding: 16px;
}

.compare-card {
  min-height: 500px;
}

.compare-card-inner {
  margin-bottom: 12px;
}

.selected-stocks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stock-tag {
  font-size: 14px;
  padding: 4px 8px;
}

.hint {
  font-size: 12px;
  color: #999;
}

.quote-card {
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.quote-card:hover {
  background: #e6f7ff;
}

.quote-name {
  font-weight: 600;
  margin-bottom: 4px;
}

.quote-price {
  font-size: 20px;
  font-weight: 700;
}

.quote-change {
  font-size: 13px;
  margin-left: 4px;
}

.quote-meta {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.price-up { color: #cf1322; }
.price-down { color: #389e0d; }

.compare-chart {
  height: 280px;
}

.cell-best {
  color: #52c41a;
  font-weight: 600;
}

.cell-worst {
  color: #cf1322;
}
</style>
