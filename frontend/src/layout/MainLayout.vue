<template>
  <div class="main-layout">
    <!-- 顶部条 -->
    <header class="top-bar">
      <div class="top-bar-inner">
        <div class="logo-area" @click="$router.push('/')" style="cursor: pointer;">
          <span class="logo-text">FinScan</span>
          <span class="logo-sub">财务分析</span>
        </div>

        <!-- 搜索框 -->
        <div class="search-box">
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="输入股票代码或名称搜索"
            class="search-input"
            @keyup.enter="handleSearch"
            @input="onSearchInput"
            @focus="showSearchResult = true"
          />
          <button class="search-btn" @click="handleSearch">搜索</button>
          <div v-if="showSearchResult && searchResults.length > 0" class="search-result">
            <div
              v-for="item in searchResults"
              :key="item.stock_code"
              class="search-result-item"
              @click="goToStock(item)"
            >
              <span class="code">{{ item.stock_code }}</span>
              <span class="name">{{ item.stock_name }}</span>
              <span v-if="item.industry" class="industry">{{ item.industry }}</span>
            </div>
          </div>
        </div>

        <!-- 用户信息 -->
        <div class="user-area">
          <span class="user-name">{{ authStore.username }}</span>
          <button class="logout-btn" @click="handleLogout">退出</button>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { stockApi, type SearchResult } from '@/api/finance'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const searchKeyword = ref('')
const showSearchResult = ref(false)
const searchResults = ref<SearchResult[]>([])
let searchTimer: number | null = null

onMounted(() => {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    if (!target.closest('.search-box')) {
      showSearchResult.value = false
    }
  })
})

watch(searchKeyword, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!val || val.length < 1) {
    searchResults.value = []
    return
  }
  searchTimer = window.setTimeout(async () => {
    try {
      const res = await stockApi.search(val)
      if (res.code === 0) {
        searchResults.value = res.data || []
        showSearchResult.value = true
      }
    } catch (e) {
      console.error(e)
    }
  }, 300)
})

function onSearchInput() {
  showSearchResult.value = true
}

function handleSearch() {
  if (searchResults.value.length > 0) {
    goToStock(searchResults.value[0])
  }
}

function goToStock(item: SearchResult) {
  showSearchResult.value = false
  searchKeyword.value = ''
  router.push(`/stock/${item.stock_code}/main-indicators`)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  background: #f5f6fa;
}

.top-bar {
  background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%);
  height: 56px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.top-bar-inner {
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-area {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.logo-text {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.logo-sub {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  width: 420px;
}

.search-input {
  flex: 1;
  height: 36px;
  border: none;
  border-radius: 4px 0 0 4px;
  padding: 0 12px;
  font-size: 14px;
  outline: none;
  background: #fff;
}

.search-btn {
  height: 36px;
  padding: 0 20px;
  border: none;
  background: #f59e0b;
  color: #fff;
  font-size: 14px;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  font-weight: 500;
}

.search-btn:hover {
  background: #d97706;
}

.search-result {
  position: absolute;
  top: 40px;
  left: 0;
  right: 68px;
  background: #fff;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-height: 300px;
  overflow-y: auto;
  z-index: 200;
}

.search-result-item {
  padding: 10px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #f0f0f0;
  color: #333;
}

.search-result-item:hover {
  background: #f0f7ff;
}

.search-result-item .code {
  color: #1d4ed8;
  font-weight: 600;
  font-size: 14px;
  min-width: 70px;
}

.search-result-item .name {
  font-size: 14px;
  flex: 1;
}

.search-result-item .industry {
  font-size: 12px;
  color: #999;
}

.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  color: #fff;
  font-size: 14px;
}

.logout-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px 24px;
}
</style>
