<template>
  <div class="fin-table-wrapper">
    <!-- 表头切换区域 -->
    <div class="table-toolbar">
      <div class="view-toggle">
        <a-radio-group v-model:value="currentView" button-style="solid" size="small" @change="onViewChange">
          <a-radio-button value="report">按报告期</a-radio-button>
          <a-radio-button value="annual">按年度</a-radio-button>
        </a-radio-group>
      </div>
      <div class="period-pager">
        <span class="pager-btn" @click="goLater" title="返回最新">‹</span>
        <span class="current-period">{{ currentPeriodText }}</span>
        <span class="pager-btn" @click="goEarlier" title="上一期">›</span>
      </div>
    </div>

    <a-spin :spinning="loading">
      <div class="fin-table-container">
        <table class="fin-table">
          <thead>
            <tr>
              <th class="fin-th col-name"></th>
              <th
                v-for="(date, idx) in reportDates"
                :key="date"
                class="fin-th col-date"
              >
                {{ formatDate(date) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(section, sIdx) in sections" :key="sIdx">
              <tr class="section-header-row">
                <td
                  :colspan="reportDates.length + 1"
                  class="section-header"
                  :class="{ 'is-total': isTotalRow(section.name) }"
                >
                  {{ section.name }}
                </td>
              </tr>
              <tr v-for="(item, iIdx) in section.items" :key="iIdx" class="data-row" :class="{ 'is-total': isTotalRow(item.name) }">
                <td class="fin-td item-name" :title="item.name">{{ item.name }}</td>
                <td
                  v-for="(val, vIdx) in item.values"
                  :key="vIdx"
                  class="fin-td item-value"
                  :class="getValueClass(item, val)"
                >
                  {{ formatValue(item.key, val) }}
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <a-empty v-if="!loading && reportDates.length === 0" description="暂无数据，请先采集该股票数据" style="padding: 60px 0" />
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface TableItem {
  name: string
  key: string
  values: (number | null)[]
}

interface TableSection {
  name: string
  items: TableItem[]
}

interface TableResponse {
  code: number
  data: {
    report_dates: string[]
    report_names?: string[]
    sections: TableSection[]
  }
}

const props = defineProps<{
  fetchData: (code: string, view: string, quarters: number, reportType?: string) => Promise<TableResponse>
  stockCode: string
  highlightTotals?: boolean
}>()

const loading = ref(false)
const currentView = ref('report')
// 窗口大小：每次显示的期数
const windowSize = ref(6)
// 窗口起始索引（0表示最新一期）
const startIdx = ref(0)
// 所有报告期（从后端加载）
const allReportDates = ref<string[]>([])
const allReportNames = ref<string[]>([])
const reportDates = ref<string[]>([])
const sections = ref<TableSection[]>([])
// 是否还有更多早期数据
const hasMoreEarlier = ref(false)

const canGoEarlier = computed(() => hasMoreEarlier.value)
const canGoLater = computed(() => startIdx.value > 0)

const currentPeriodText = computed(() => {
  if (!reportDates.value.length) return '-'
  const first = reportDates.value[0]
  const last = reportDates.value[reportDates.value.length - 1]
  return `${formatDate(first)} ~ ${formatDate(last)}`
})

function goEarlier() {
  if (canGoEarlier.value) {
    startIdx.value += 1
    loadData()
  }
}

function goLater() {
  if (canGoLater.value) {
    startIdx.value = Math.max(0, startIdx.value - 1)
    loadData()
  }
}

function onViewChange() {
  startIdx.value = 0
  loadData()
}

async function loadData() {
  if (!props.stockCode) return
  loading.value = true
  try {
    // 多请求1期作为探针，用于判断是否还有更早的数据
    const fetchLimit = startIdx.value + windowSize.value + 1
    // annual视图时传递reportType="Annual"
    const reportType = currentView.value === 'annual' ? 'Annual' : undefined
    const res = await props.fetchData(props.stockCode, currentView.value, fetchLimit, reportType)
    if (res.code === 0 && res.data) {
      allReportDates.value = res.data.report_dates || []
      allReportNames.value = res.data.report_names || []
      // 判断是否还有更多早期数据
      hasMoreEarlier.value = allReportDates.value.length > startIdx.value + windowSize.value
      // 切片：从 startIdx 开始取 windowSize 个
      const end = Math.min(startIdx.value + windowSize.value, allReportDates.value.length)
      reportDates.value = allReportDates.value.slice(startIdx.value, end)
      // 同时切片 sections 里的 values
      const sliced = (res.data.sections || []).map((sec: TableSection) => ({
        name: sec.name,
        items: sec.items.map((item) => ({
          name: item.name,
          key: item.key,
          values: item.values.slice(startIdx.value, end),
        })),
      }))
      sections.value = sliced
    } else {
      allReportDates.value = []
      allReportNames.value = []
      reportDates.value = []
      sections.value = []
      hasMoreEarlier.value = false
    }
  } catch (e) {
    console.error(e)
    allReportDates.value = []
    allReportNames.value = []
    reportDates.value = []
    sections.value = []
    hasMoreEarlier.value = false
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  return dateStr.slice(0, 10)
}

function formatValue(key: string, val: number | null): string {
  if (val === null || val === undefined) return '-'
  const lowerKey = key.toLowerCase()
  // 比率类（%）字段：精确匹配常见比率字段名模式
  const ratePatterns = [
    /_ratio$/, /_rate$/, /_yoy$/, /_qoq$/, /_margin$/, /_growth$/, /_percent$/,
    /^roe/, /^roa/, /^zcfzl/, /^xsmll/, /^xsjll/, /^zzcjll/, /^ld$/, /^sd$/, /^xjllb/,
    /_turnover$/, /_turnover_days$/,
  ]
  const isRatio = ratePatterns.some(p => p.test(lowerKey)) ||
    ['roe', 'roa', 'debt_ratio', 'current_ratio', 'quick_ratio', 'gross_margin',
     'net_margin', 'asset_turnover', 'inventory_turnover', 'receivable_turnover',
     'revenue_yoy', 'net_profit_yoy', 'gross_profit_yoy',
     // 收益质量指标
     'yszkzzl', 'yszkzzyl', 'xsjxl', 'jyxjl', 'jyxjljlr', 'zbzczjtx',
     'yszkzzts', 'toazzl', 'chzzl',
    ].includes(lowerKey)
  if (isRatio) {
    return val.toFixed(2) + '%'
  }
  // 每股指标（EPS/BPS等），单位元，保留4位
  if (lowerKey.includes('eps') || lowerKey.includes('bps') || lowerKey.endsWith('_ps') || key === 'BASIC_EPS' || key === 'DILUTED_EPS') {
    return val.toFixed(4)
  }
  // 金额类字段：自动转换为万/亿
  const absVal = Math.abs(val)
  if (absVal >= 1e8) {
    return (val / 1e8).toFixed(2) + '亿'
  } else if (absVal >= 1e4) {
    return (val / 1e4).toFixed(2) + '万'
  }
  // 流动比率/速动比率等
  if (lowerKey === 'ld' || lowerKey === 'sd' || lowerKey.includes('current_ratio') || lowerKey.includes('quick_ratio')) {
    return val.toFixed(2)
  }
  return val.toFixed(2)
}

function getValueClass(item: TableItem, val: number | null) {
  if (val === null) return ''
  const key = item.key.toLowerCase()
  // 同比增长率
  if (key.includes('yoy') || key.includes('qoq') || key.includes('growth')) {
    return val >= 0 ? 'val-up' : 'val-down'
  }
  // ROE 等盈利指标
  if (key.includes('roe') || key.includes('roa')) {
    if (val >= 15) return 'val-good'
    if (val >= 8) return 'val-ok'
    return val >= 0 ? 'val-weak' : 'val-down'
  }
  // 利润类
  if (key.includes('profit') || key.includes('income') || key.includes('revenue')) {
    if (key.endsWith('_yoy') || key.endsWith('_growth')) return val >= 0 ? 'val-up' : 'val-down'
    return val >= 0 ? '' : 'val-down'
  }
  return ''
}

function isTotalRow(name: string): boolean {
  if (!props.highlightTotals) return false
  const totalItems = [
    '流动资产合计', '非流动资产合计',
    '流动负债合计', '非流动负债合计',
    '资产总计', '负债合计',
    '归属于母公司股东权益合计', '归属于母公司股东权益总计',
    '股东权益合计', '负债和股东权益合计',
  ]
  return totalItems.includes(name)
}

watch(() => props.stockCode, () => {
  if (props.stockCode) {
    startIdx.value = 0
    loadData()
  }
}, { immediate: true })
</script>

<style scoped>
.fin-table-wrapper {
  width: 100%;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.period-pager {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pager-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  font-size: 18px;
  font-weight: 600;
  color: #1d4ed8;
  background: #f0f7ff;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s;
}

.pager-btn:hover {
  background: #dbeafe;
  color: #1d40dc;
}

.pager-btn:active {
  transform: scale(0.95);
}

.period-label {
  font-size: 13px;
  color: #666;
}

.current-period {
  display: inline-block;
  min-width: 180px;
  text-align: center;
  font-size: 13px;
  color: #1d4ed8;
  font-weight: 600;
  padding: 4px 8px;
  background: #f0f7ff;
  border-radius: 4px;
}

.fin-table-container {
  overflow-x: auto;
}

.fin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.fin-th {
  background: #fafafa;
  padding: 10px 12px;
  text-align: right;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e8e8e8;
  white-space: nowrap;
}

.fin-th:first-child {
  text-align: left;
  position: sticky;
  left: 0;
  z-index: 10;
  min-width: 220px;
  max-width: 300px;
  background: #fafafa;
}

.col-date {
  min-width: 110px;
}

.section-header-row td {
  padding: 0;
}

.section-header {
  background: linear-gradient(to right, #f0f7ff, #fff);
  color: #1d4ed8;
  font-weight: 600;
  font-size: 13px;
  padding: 10px 12px;
  border-bottom: 1px solid #e6f4ff;
}

/* 合计行：加粗突出，无背景色 */
.section-header.is-total {
  background: transparent;
  color: #333;
  font-weight: 700;
  font-size: 13px;
  border-top: 2px solid #e8e8e8;
  border-bottom: 2px solid #d0d0d0;
}

.data-row:hover td {
  background: #f8fafc;
}

.data-row.is-total td {
  font-weight: 700;
  color: #111;
  background: #fafafa;
  border-top: 2px solid #e0e0e0;
  border-bottom: 2px solid #d0d0d0;
}

.data-row.is-total .item-name {
  font-weight: 700;
  background: #fafafa;
}

.fin-td {
  padding: 9px 12px;
  border-bottom: 1px solid #f5f5f5;
  text-align: right;
  color: #333;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.fin-td.item-name {
  text-align: left;
  position: sticky;
  left: 0;
  background: #fff;
  color: #555;
  z-index: 5;
  font-weight: 400;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

.data-row:hover .fin-td.item-name {
  background: #f8fafc;
}

.val-up {
  color: #cf1322;
}

.val-down {
  color: #389e0d;
}

.val-good {
  color: #cf1322;
  font-weight: 600;
}

.val-ok {
  color: #d48806;
}

.val-weak {
  color: #8c8c8c;
}
</style>
