<template>
  <a-auto-complete
    v-model:value="keyword"
    :options="searchResults"
    placeholder="搜索股票代码或名称..."
    class="global-search"
    @search="handleSearch"
    @select="handleSelect"
  >
    <template #option="{ item }">
      <div class="search-option">
        <span class="stock-name">{{ item.stock_name }}</span>
        <span class="stock-code">{{ item.stock_code }}</span>
        <a-tag v-if="item.is_st" color="red">ST</a-tag>
      </div>
    </template>
  </a-auto-complete>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { searchStocks } from '@/api/stock'

const props = withDefaults(defineProps<{
  noNavigate?: boolean
}>(), {
  noNavigate: false,
})

const emit = defineEmits<{
  select: [item: { stock_code: string; stock_name: string }]
}>()

const router = useRouter()
const keyword = ref('')
const searchResults = ref<any[]>([])

let searchTimer: ReturnType<typeof setTimeout> | null = null

const handleSearch = (value: string) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!value || value.length < 1) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    try {
      const response = await searchStocks({ keyword: value, page: 1, page_size: 10 })
      if (response.data.code === 200) {
        searchResults.value = (response.data.data.items || []).map((i: any) => ({
          ...i,
          value: i.stock_code,
        }))
      }
    } catch (error) {
      console.error('Search failed:', error)
    }
  }, 300)
}

const handleSelect = (stockCode: string) => {
  const item = searchResults.value.find(i => i.stock_code === stockCode)
  if (!item) return

  emit('select', { stock_code: item.stock_code, stock_name: item.stock_name })

  if (!props.noNavigate) {
    router.push(`/stock/${stockCode}`)
  }

  keyword.value = ''
  searchResults.value = []
}
</script>

<style scoped>
.global-search {
  width: 100%;
}

.search-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-name {
  font-weight: 500;
}

.stock-code {
  color: #999;
  font-family: 'SF Mono', 'Consolas', monospace;
}
</style>
