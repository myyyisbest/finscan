<template>
  <div class="fin-table">
    <div class="table-controls">
      <a-radio-group v-model:value="reportType" button-style="solid" @change="handleReportTypeChange">
        <a-radio-button value="annual">年报</a-radio-button>
        <a-radio-button value="quarter">季报</a-radio-button>
        <a-radio-button value="all">全部</a-radio-button>
      </a-radio-group>
      <a-radio-group v-model:value="unit" button-style="solid">
        <a-radio-button value="yuan">元</a-radio-button>
        <a-radio-button value="ten-thousand">万元</a-radio-button>
      </a-radio-group>
    </div>
    <a-table
      :columns="columns"
      :data-source="tableData"
      :pagination="pagination"
      :loading="loading"
      :scroll="{ x: 'max-content' }"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'report_date'">
          <span class="mono-number">{{ record.report_date }}</span>
        </template>
        <template v-else-if="column.key === 'report_type'">
          <a-tag :color="getReportTypeColor(record.report_type)">
            {{ getReportTypeLabel(record.report_type) }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'value'">
          <span
            class="mono-number"
            :class="getValueClass(record.value)"
          >
            {{ formatValue(record.value) }}
          </span>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

type TableType = 'balance' | 'income' | 'cashflow' | 'indicators'

const props = defineProps<{
  type: TableType
  stockCode: string
}>()

const emit = defineEmits(['data-loaded'])

const loading = ref(false)
const reportType = ref('annual')
const unit = ref('ten-thousand')
const allData = ref<any[]>([])
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0
})

const columns = computed(() => {
  const baseColumns = [
    {
      title: '报告日期',
      dataIndex: 'report_date',
      key: 'report_date',
      width: 120,
      sorter: (a: any, b: any) => a.report_date.localeCompare(b.report_date)
    },
    {
      title: '报告类型',
      dataIndex: 'report_type',
      key: 'report_type',
      width: 100
    }
  ]

  if (props.type === 'indicators') {
    return [
      ...baseColumns,
      { title: 'ROE', dataIndex: 'roe', key: 'roe', width: 100 },
      { title: 'ROA', dataIndex: 'roa', key: 'roa', width: 100 },
      { title: '毛利率', dataIndex: 'gross_margin', key: 'gross_margin', width: 100 },
      { title: '净利率', dataIndex: 'net_margin', key: 'net_margin', width: 100 },
      { title: '资产负债率', dataIndex: 'debt_to_assets', key: 'debt_to_assets', width: 120 },
      { title: '流动比率', dataIndex: 'current_ratio', key: 'current_ratio', width: 100 },
      { title: '速动比率', dataIndex: 'quick_ratio', key: 'quick_ratio', width: 100 }
    ]
  }

  return [
    ...baseColumns,
    { title: '项目', dataIndex: 'item_name', key: 'item_name', width: 200 },
    {
      title: '金额',
      dataIndex: 'value',
      key: 'value',
      width: 150,
      sorter: (a: any, b: any) => (a.value || 0) - (b.value || 0)
    },
    { title: '单位', dataIndex: 'unit', key: 'unit', width: 80 }
  ]
})

const tableData = computed(() => {
  let filtered = allData.value

  if (reportType.value !== 'all') {
    filtered = filtered.filter((item: any) => {
      if (reportType.value === 'annual') {
        return item.report_type === '年报' || item.report_type === '年度'
      }
      return item.report_type !== '年报' && item.report_type !== '年度'
    })
  }

  return filtered.map((item: any) => ({
    ...item,
    value: unit.value === 'ten-thousand' && item.value !== null
      ? item.value / 10000
      : item.value
  }))
})

const handleTableChange = (pag: any) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
}

const handleReportTypeChange = () => {
  pagination.value.current = 1
}

const formatValue = (value: number | null): string => {
  if (value === null || value === undefined) return '-'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const getValueClass = (value: number | null): string => {
  if (value === null || value === undefined) return ''
  return value >= 0 ? 'positive' : 'negative'
}

const getReportTypeColor = (type: string): string => {
  if (type === '年报' || type === '年度') return 'blue'
  if (type === '一季报' || type === 'Q1') return 'green'
  if (type === '中报' || type === '半年报') return 'orange'
  if (type === '三季报' || type === 'Q3') return 'purple'
  return 'default'
}

const getReportTypeLabel = (type: string): string => {
  return type
}

const loadData = async () => {
  loading.value = true
  try {
    const { getBalanceSheet, getIncomeStatement, getCashFlow, getIndicators } = await import('@/api/stock')
    
    let response
    switch (props.type) {
      case 'balance':
        response = await getBalanceSheet(props.stockCode, { page: 1, page_size: 100 })
        break
      case 'income':
        response = await getIncomeStatement(props.stockCode, { page: 1, page_size: 100 })
        break
      case 'cashflow':
        response = await getCashFlow(props.stockCode, { page: 1, page_size: 100 })
        break
      case 'indicators':
        response = await getIndicators(props.stockCode, { page: 1, page_size: 100 })
        break
    }

    if (response.data.code === 200) {
      allData.value = response.data.data.items || []
      pagination.value.total = allData.value.length
      emit('data-loaded', allData.value)
    }
  } catch (error) {
    console.error('Failed to load table data:', error)
  } finally {
    loading.value = false
  }
}

watch(() => props.stockCode, () => {
  loadData()
})

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.fin-table {
  width: 100%;
}

.table-controls {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
</style>
