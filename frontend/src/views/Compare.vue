<template>
  <div class="compare-page">
    <a-card title="公司财务对比" class="compare-card">
      <template #extra>
        <a-space>
          <GlobalSearch no-navigate @select="handleAddStock" />
          <a-button @click="resetCompare">重置</a-button>
        </a-space>
      </template>

      <a-spin :spinning="loading">
        <a-row :gutter="16" v-if="selectedStocks.length > 0">
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

        <!-- 指标对比表 -->
        <a-table
          v-if="compareData.length > 0"
          :columns="compareColumns"
          :data-source="compareData"
          :pagination="false"
          bordered
          size="small"
          class="compare-table"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key !== 'indicator'">
              <span :class="getCompareClass(record, column.key)">
                {{ record[column.key] || '-' }}
              </span>
            </template>
            <template v-else>
              <b>{{ record.indicator }}</b>
            </template>
          </template>
        </a-table>

        <a-empty v-if="selectedStocks.length === 0" description="请添加股票进行对比">
          <template #image>
            <BarChartOutlined style="font-size: 48px; color: #ccc" />
          </template>
        </a-empty>
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { BarChartOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import GlobalSearch from '@/components/GlobalSearch.vue'
import { getStockOverview } from '@/api/stock'

const loading = ref(false)
const selectedStocks = ref<any[]>([])

const compareData = ref<any[]>([])

const compareColumns = computed(() => {
  const cols: any[] = [{ title: '指标', key: 'indicator', fixed: 'left', width: 140 }]
  selectedStocks.value.forEach(s => {
    cols.push({ title: `${s.stock_name}(${s.stock_code})`, key: s.stock_code, width: 160 })
  })
  return cols
})

const indicators = [
  { key: 'pe', label: '市盈率(PE)' },
  { key: 'pb', label: '市净率(PB)' },
  { key: 'roe', label: 'ROE(%)' },
  { key: 'gross_margin', label: '毛利率(%)' },
  { key: 'net_margin', label: '净利润率(%)' },
  { key: 'revenue_growth', label: '营收增长率(%)' },
  { key: 'profit_growth', label: '净利润增长率(%)' },
  { key: 'debt_ratio', label: '资产负债率(%)' },
]

const handleAddStock = async (item: { stock_code: string; stock_name: string }) => {
  if (selectedStocks.value.find(s => s.stock_code === item.stock_code)) {
    message.warning('已添加该股票')
    return
  }
  if (selectedStocks.value.length >= 4) {
    message.warning('最多对比4家公司')
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
}

const loadCompare = async () => {
  if (selectedStocks.value.length === 0) {
    compareData.value = []
    return
  }
  loading.value = true
  try {
    const allOverviews = await Promise.all(
      selectedStocks.value.map(s => getStockOverview(s.stock_code))
    )
    const overviewMap: Record<string, any> = {}
    allOverviews.forEach((res, i) => {
      if (res.data.code === 200) {
        overviewMap[selectedStocks.value[i].stock_code] = res.data.data.overview || {}
      }
    })

    compareData.value = indicators.map(ind => {
      const row: any = { indicator: ind.label, key: ind.key }
      selectedStocks.value.forEach(s => {
        const ov = overviewMap[s.stock_code] || {}
        let val = ov[ind.key]
        if (ind.key === 'roe' || ind.key === 'gross_margin' || ind.key === 'net_margin' ||
            ind.key === 'revenue_growth' || ind.key === 'profit_growth' || ind.key === 'debt_ratio') {
          val = val != null ? val.toFixed(2) + '%' : '-'
        }
        row[s.stock_code] = val != null ? val : '-'
      })
      return row
    })
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const getCompareClass = (record: any, code: string) => {
  const val = parseFloat(record[code])
  if (isNaN(val)) return ''
  const values = selectedStocks.value.map(s => parseFloat(record[s.stock_code])).filter(v => !isNaN(v))
  const max = Math.max(...values)
  const min = Math.min(...values)
  if (record.indicator === '资产负债率(%)' || record.indicator === '市盈率(PE)') {
    return val === min ? 'cell-best' : val === max ? 'cell-worst' : ''
  }
  return val === max ? 'cell-best' : val === min ? 'cell-worst' : ''
}

onMounted(() => {
  // Preload from watchlist if available
})
</script>

<style scoped>
.compare-page {
  padding: 16px;
}

.compare-card {
  min-height: 500px;
}

.selected-stocks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.stock-tag {
  font-size: 14px;
  padding: 4px 8px;
}

.compare-table {
  margin-top: 16px;
}

.cell-best {
  color: #52c41a;
  font-weight: 600;
}

.cell-worst {
  color: #cf1322;
}
</style>
