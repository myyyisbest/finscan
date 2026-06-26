<template>
  <div class="fin-table-wrapper">
    <!-- 表头切换区域 -->
    <div class="table-toolbar">
      <div class="view-toggle">
        <a-radio-group v-model:value="currentView" button-style="solid" size="small" @change="loadData">
          <a-radio-button value="report">按报告期</a-radio-button>
        </a-radio-group>
      </div>
      <div class="period-select">
        <span class="period-label">显示期数：</span>
        <a-select v-model:value="quarters" size="small" style="width: 100px" @change="loadData">
          <a-select-option :value="4">4期</a-select-option>
          <a-select-option :value="8">8期</a-select-option>
          <a-select-option :value="12">12期</a-select-option>
        </a-select>
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
              <tr v-for="(item, iIdx) in section.items" :key="iIdx" class="data-row">
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
import { ref, watch } from 'vue'

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
    sections: TableSection[]
  }
}

const props = defineProps<{
  fetchData: (code: string, view: string, quarters: number) => Promise<TableResponse>
  stockCode: string
}>()

const loading = ref(false)
const currentView = ref('report')
const quarters = ref(8)
const reportDates = ref<string[]>([])
const sections = ref<TableSection[]>([])

async function loadData() {
  loading.value = true
  try {
    const res = await props.fetchData(props.stockCode, currentView.value, quarters.value)
    if (res.code === 0 && res.data) {
      reportDates.value = res.data.report_dates || []
      sections.value = res.data.sections || []
    } else {
      reportDates.value = []
      sections.value = []
    }
  } catch (e) {
    console.error(e)
    reportDates.value = []
    sections.value = []
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

// 判断是否为合计行
const totalRowNames = [
  '流动资产合计', '非流动资产合计', '资产总计',
  '流动负债合计', '非流动负债合计', '负债合计',
  '股东权益合计', '负债和股东权益合计',
  '经营活动现金流入小计', '经营活动现金流出小计', '经营活动产生的现金流量净额',
  '投资活动现金流入小计', '投资活动现金流出小计', '投资活动产生的现金流量净额',
  '筹资活动现金流入小计', '筹资活动现金流出小计', '筹资活动产生的现金流量净额',
  '现金及现金等价物净增加额',
]
function isTotalRow(name: string): boolean {
  return totalRowNames.includes(name)
}

watch(() => props.stockCode, () => {
  if (props.stockCode) {
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

.period-label {
  font-size: 13px;
  color: #666;
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
