<template>
  <div class="stock-search-page">
    <a-card class="search-card">
      <h2 class="section-title">股票检索</h2>
      <a-input-search
        v-model:value="keyword"
        placeholder="输入股票代码或名称 (如: 600879 / 航天电子)"
        enter-button="搜索"
        size="large"
        @search="handleSearch"
        allow-clear
      />
    </a-card>

    <a-card class="result-card" :title="`搜索结果 (${total} 条)`">
      <a-spin :spinning="loading">
        <a-table
          :columns="columns"
          :data-source="results"
          :pagination="false"
          row-key="stock_code"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'stock_code'">
              <a @click="goDetail(record.stock_code)">{{ record.stock_code }}</a>
            </template>
            <template v-else-if="column.key === 'stock_name'">
              <span :class="{ 'st-tag': record.is_st }">{{ record.stock_name }}</span>
              <a-tag v-if="record.is_st" color="red" size="small" style="margin-left: 4px">ST</a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="primary" size="small" @click="addToWatchlist(record)">
                + 加入自选
              </a-button>
            </template>
          </template>
        </a-table>
        <a-empty v-if="!loading && results.length === 0" description="暂无结果,请输入股票代码或名称" />
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { searchStocks } from '@/api/stock'
import { addToWatchlist as addStockToWatchlist } from '@/api/watchlist'
import type { StockSearchItem } from '@/types'

const router = useRouter()
const keyword = ref('')
const loading = ref(false)
const results = ref<StockSearchItem[]>([])
const total = ref(0)

const columns = [
  { title: '代码', dataIndex: 'stock_code', key: 'stock_code', width: 140 },
  { title: '名称', dataIndex: 'stock_name', key: 'stock_name', width: 180 },
  { title: '行业', dataIndex: 'industry', key: 'industry' },
  { title: '市场', dataIndex: 'market', key: 'market', width: 100 },
  { title: '操作', key: 'action', width: 140 },
]

const loadAll = async () => {
  loading.value = true
  try {
    const response = await searchStocks({ keyword: '', page: 1, page_size: 50 })
    if (response.data.code === 200) {
      results.value = (response.data.data.items || []).map((i: any) => ({ ...i, value: i.stock_code }))
      total.value = response.data.data.total || 0
    }
  } catch (error) {
    console.error('Failed to load stocks:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = async (value: string) => {
  loading.value = true
  try {
    const response = await searchStocks({ keyword: value, page: 1, page_size: 50 })
    if (response.data.code === 200) {
      results.value = (response.data.data.items || []).map((i: any) => ({ ...i, value: i.stock_code }))
      total.value = response.data.data.total || 0
    }
  } catch (error) {
    console.error('Search failed:', error)
  } finally {
    loading.value = false
  }
}

const goDetail = (code: string) => {
  router.push(`/stock/${code}`)
}

const addToWatchlist = async (stock: StockSearchItem) => {
  try {
    await addStockToWatchlist({
      stock_code: stock.stock_code,
      stock_name: stock.stock_name,
      group_name: '默认分组',
    })
    message.success(`已加入自选: ${stock.stock_name}`)
  } catch (error) {
    message.error('加入自选失败,请先登录')
  }
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.stock-search-page {
  padding: 16px;
}

.search-card {
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 12px;
  color: #333;
}

.st-tag {
  color: #ff4d4f;
}
</style>
