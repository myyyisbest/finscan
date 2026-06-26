<template>
  <div class="stock-detail">
    <!-- 股票头部信息栏（类似东财F10蓝色头部） -->
    <div class="stock-header">
      <div class="stock-header-inner">
        <div class="stock-title-area" v-if="stockInfo">
          <div class="stock-code-badge">
            <span class="market-tag">{{ stockInfo.market }}</span>
            <span class="stock-code">{{ stockInfo.stock_code }}</span>
          </div>
          <h1 class="stock-name">{{ stockInfo.stock_name }}</h1>
          <span v-if="stockInfo.industry" class="stock-industry">{{ stockInfo.industry }}</span>
          <button class="watchlist-btn" @click="toggleWatchlist">
            <StarOutlined v-if="isInWatchlist" style="color: #f59e0b" />
            <StarOutlined v-else />
            {{ isInWatchlist ? '已自选' : '加自选' }}
          </button>
        </div>
        <a-spin v-else size="small" />
      </div>

      <!-- 一级Tab导航（类似东财：操盘必读/财务分析/公告...） -->
      <div class="nav-tabs">
        <div class="nav-tabs-inner">
          <router-link
            v-for="tab in mainTabs"
            :key="tab.path"
            :to="tab.path"
            class="nav-tab"
            :class="{ active: isTabActive(tab.path) }"
          >
            {{ tab.name }}
          </router-link>
        </div>
      </div>
    </div>

    <!-- 财务分析二级导航 -->
    <div v-if="isFinanceTab" class="sub-nav">
      <div class="sub-nav-inner">
        <router-link
          v-for="tab in financeSubTabs"
          :key="tab.path"
          :to="tab.path"
          class="sub-nav-tab"
          :class="{ active: route.path.startsWith(tab.path) }"
        >
          {{ tab.name }}
        </router-link>
      </div>
    </div>

    <!-- 子页面内容 -->
    <div class="detail-content">
      <router-view v-slot="{ Component }">
        <a-spin :spinning="pageLoading">
          <component :is="Component" :stock-code="stockCode" :stock-info="stockInfo" />
        </a-spin>
      </router-view>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { StarOutlined } from '@ant-design/icons-vue'
import { stockApi, watchlistApi, type StockInfo } from '@/api/finance'

const route = useRoute()
const router = useRouter()
const stockCode = computed(() => (route.params.code as string))
const stockInfo = ref<StockInfo | null>(null)
const pageLoading = ref(false)
const isInWatchlist = ref(false)

const mainTabs = [
  { name: '财务分析', path: `/stock/${stockCode.value}/main-indicators` },
  { name: '公司公告', path: `/stock/${stockCode.value}/announcements` },
]

const financeSubTabs = computed(() => [
  { name: '主要指标', path: `/stock/${stockCode.value}/main-indicators` },
  { name: '杜邦分析', path: `/stock/${stockCode.value}/dupont-analysis` },
  { name: '资产负债表', path: `/stock/${stockCode.value}/balance-sheet` },
  { name: '利润表', path: `/stock/${stockCode.value}/income-statement` },
  { name: '现金流量表', path: `/stock/${stockCode.value}/cash-flow` },
])

const isFinanceTab = computed(() => {
  const p = route.path
  return p.endsWith('/main-indicators') || p.endsWith('/dupont-analysis') ||
         p.endsWith('/balance-sheet') || p.endsWith('/income-statement') ||
         p.endsWith('/cash-flow')
})

function isTabActive(path: string) {
  if (path.endsWith('/announcements')) return route.path.endsWith('/announcements')
  if (path.endsWith('/main-indicators')) return route.path.endsWith('/main-indicators') ||
                                              route.path.endsWith('/dupont-analysis') ||
                                              route.path.endsWith('/balance-sheet') ||
                                              route.path.endsWith('/income-statement') ||
                                              route.path.endsWith('/cash-flow')
  return route.path.startsWith(path)
}

async function loadStockInfo() {
  if (!stockCode.value) return
  pageLoading.value = true
  try {
    const res = await stockApi.getInfo(stockCode.value)
    if (res.code === 0) {
      stockInfo.value = res.data
      // 更新tab路径
      mainTabs[0].path = `/stock/${stockCode.value}/main-indicators`
      mainTabs[1].path = `/stock/${stockCode.value}/announcements`
    }
  } catch (e) {
    console.error(e)
  } finally {
    pageLoading.value = false
  }
}

async function checkWatchlist() {
  try {
    const res = await watchlistApi.list()
    if (res.code === 0) {
      isInWatchlist.value = (res.data || []).some(s => s.stock_code === stockCode.value)
    }
  } catch (e) {
    console.error(e)
  }
}

async function toggleWatchlist() {
  try {
    if (isInWatchlist.value) {
      await watchlistApi.remove(stockCode.value)
      message.success('已从自选移除')
      isInWatchlist.value = false
    } else {
      await watchlistApi.add(stockCode.value, stockInfo.value?.stock_name)
      message.success('已添加到自选')
      isInWatchlist.value = true
    }
  } catch (e: any) {
    message.error(e?.response?.data?.message || '操作失败')
  }
}

watch(stockCode, () => {
  loadStockInfo()
  checkWatchlist()
})

onMounted(() => {
  loadStockInfo()
  checkWatchlist()
})
</script>

<style scoped>
.stock-detail {
  min-height: calc(100vh - 96px);
}

.stock-header {
  background: #fff;
  border-radius: 8px 8px 0 0;
  margin-bottom: 0;
}

.stock-header-inner {
  padding: 20px 24px 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stock-title-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stock-code-badge {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #1d4ed8, #1e40af);
  color: #fff;
  padding: 6px 12px;
  border-radius: 6px;
  gap: 6px;
}

.market-tag {
  font-size: 11px;
  opacity: 0.8;
  font-weight: 500;
}

.stock-code {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1px;
}

.stock-name {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
}

.stock-industry {
  font-size: 13px;
  color: #666;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 4px;
}

.watchlist-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #e8e8e8;
  background: #fff;
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  color: #666;
  margin-left: 16px;
}

.watchlist-btn:hover {
  border-color: #1d4ed8;
  color: #1d4ed8;
}

.nav-tabs {
  border-top: 1px solid #f0f0f0;
}

.nav-tabs-inner {
  display: flex;
  padding: 0 24px;
}

.nav-tab {
  padding: 12px 20px;
  font-size: 14px;
  color: #666;
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  cursor: pointer;
}

.nav-tab:hover {
  color: #1d4ed8;
}

.nav-tab.active {
  color: #1d4ed8;
  font-weight: 600;
  border-bottom-color: #1d4ed8;
}

.sub-nav {
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.sub-nav-inner {
  display: flex;
  padding: 0 24px;
}

.sub-nav-tab {
  padding: 10px 24px;
  font-size: 13px;
  color: #666;
  text-decoration: none;
  cursor: pointer;
}

.sub-nav-tab:hover {
  color: #1d4ed8;
}

.sub-nav-tab.active {
  color: #1d4ed8;
  font-weight: 600;
}

.detail-content {
  background: #fff;
  padding: 20px 24px;
  min-height: 400px;
  border-radius: 0 0 8px 8px;
}
</style>
