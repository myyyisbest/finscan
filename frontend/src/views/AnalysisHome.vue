<template>
  <div class="analysis-home">
    <!-- 顶部搜索区 -->
    <div class="hero-section">
      <div class="hero-title">
        <LineChartOutlined class="hero-icon" />
        <h1>财报分析</h1>
      </div>
      <p class="hero-sub">输入股票代码或名称，快速查看公司财务分析报告</p>

      <div class="search-hero">
        <div class="search-input-wrap">
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="输入股票代码或名称，如：600519 / 贵州茅台"
            class="search-input"
            @keyup.enter="handleSearch"
            @input="onSearchInput"
            @focus="showSearchResult = true"
          />
          <button class="search-btn" @click="handleSearch">
            <SearchOutlined /> 分析
          </button>
        </div>
        <div v-if="showSearchResult && searchResults.length > 0" class="search-result">
          <div
            v-for="item in searchResults"
            :key="item.stock_code"
            class="search-result-item"
            @click="goToStock(item.stock_code)"
          >
            <span class="code">{{ item.stock_code }}</span>
            <span class="name">{{ item.stock_name }}</span>
            <span v-if="item.industry" class="industry">{{ item.industry }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 自选股快速入口 -->
    <div class="quick-section">
      <div class="section-header">
        <h3><StarOutlined /> 我的自选 - 快速进入</h3>
        <a-tag color="blue" v-if="watchlist.length > 0">共 {{ watchlist.length }} 只</a-tag>
      </div>

      <a-spin :spinning="loading">
        <div v-if="watchlist.length > 0" class="stock-grid">
          <div
            v-for="item in watchlist"
            :key="item.stock_code"
            class="stock-card card-hover"
            @click="goToStock(item.stock_code)"
          >
            <div class="stock-info">
              <div class="stock-name">{{ item.stock_name }}</div>
              <div class="stock-code">{{ item.stock_code }}</div>
            </div>
            <div class="stock-metrics">
              <div v-if="item.latest_report?.roe != null" class="metric">
                <span class="metric-label">ROE</span>
                <span class="metric-value roe">{{ item.latest_report.roe.toFixed(2) }}%</span>
              </div>
              <div v-if="item.latest_report?.debt_ratio != null" class="metric">
                <span class="metric-label">资产负债率</span>
                <span class="metric-value">{{ item.latest_report.debt_ratio.toFixed(2) }}%</span>
              </div>
            </div>
            <div class="card-arrow">
              <ArrowRightOutlined />
            </div>
          </div>
        </div>

        <a-empty v-else-if="!loading" description="暂无自选股票">
          <template #description>
            <span>先去"我的自选"添加股票吧</span>
          </template>
        </a-empty>
      </a-spin>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  LineChartOutlined, SearchOutlined, StarOutlined, ArrowRightOutlined
} from '@ant-design/icons-vue'
import { watchlistApi } from '@/api/finance'
import { stockApi, type SearchResult } from '@/api/finance'
import type { WatchlistItem } from '@/api/finance'

const router = useRouter()

const searchKeyword = ref('')
const showSearchResult = ref(false)
const searchResults = ref<SearchResult[]>([])
const watchlist = ref<WatchlistItem[]>([])
const loading = ref(false)
let searchTimer: number | null = null

onMounted(() => {
  loadWatchlist()
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    if (!target.closest('.search-hero')) {
      showSearchResult.value = false
    }
  })
})

async function loadWatchlist() {
  loading.value = true
  try {
    const res = await watchlistApi.list()
    if (res.code === 0) {
      watchlist.value = res.data || []
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  showSearchResult.value = true
  if (searchTimer) clearTimeout(searchTimer)
  const val = searchKeyword.value
  if (!val || val.length < 1) {
    searchResults.value = []
    return
  }
  searchTimer = window.setTimeout(async () => {
    try {
      const res = await stockApi.search(val)
      if (res.code === 0) {
        searchResults.value = res.data || []
      }
    } catch (e) {
      console.error(e)
    }
  }, 300)
}

function handleSearch() {
  if (searchResults.value.length > 0) {
    goToStock(searchResults.value[0].stock_code)
  }
}

function goToStock(code: string) {
  router.push(`/stock/${code}/main-indicators`)
}
</script>

<style scoped>
.analysis-home {
  min-height: calc(100vh - 96px);
}

.fade-in { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.hero-section {
  background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%);
  border-radius: 16px;
  padding: 48px 40px;
  color: #fff;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}
.hero-section::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -10%;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
  border-radius: 50%;
}

.hero-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.hero-icon {
  font-size: 32px;
}
.hero-title h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
}
.hero-sub {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0 0 24px 0;
}

.search-hero {
  position: relative;
  max-width: 560px;
}
.search-input-wrap {
  display: flex;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}
.search-input {
  flex: 1;
  height: 48px;
  border: none;
  padding: 0 20px;
  font-size: 15px;
  outline: none;
  background: #fff;
}
.search-btn {
  height: 48px;
  padding: 0 24px;
  border: none;
  background: #f59e0b;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.2s;
}
.search-btn:hover {
  background: #d97706;
}

.search-result {
  position: absolute;
  top: 56px;
  left: 0;
  right: 0;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  max-height: 320px;
  overflow-y: auto;
  z-index: 100;
}
.search-result-item {
  padding: 12px 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #f0f0f0;
  color: #333;
  transition: background 0.15s;
}
.search-result-item:last-child { border-bottom: none; }
.search-result-item:hover { background: #f0f7ff; }
.search-result-item .code { color: #1d4ed8; font-weight: 600; font-size: 14px; min-width: 70px; }
.search-result-item .name { font-size: 14px; flex: 1; }
.search-result-item .industry { font-size: 12px; color: #999; }

/* 自选股网格 */
.quick-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e8e8e8;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.section-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}
.stock-card {
  background: #fafbfc;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;
  position: relative;
}
.card-hover:hover {
  border-color: #3b82f6;
  background: #f0f7ff;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.15);
}
.stock-info {
  flex: 1;
  min-width: 0;
}
.stock-name {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}
.stock-code {
  font-size: 12px;
  color: #999;
}
.stock-metrics {
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: right;
  min-width: 90px;
}
.metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.metric-label {
  font-size: 11px;
  color: #999;
}
.metric-value {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}
.metric-value.roe {
  color: #10b981;
}
.card-arrow {
  color: #ccc;
  font-size: 14px;
  flex-shrink: 0;
}
.stock-card:hover .card-arrow {
  color: #1d4ed8;
}
</style>
