<template>
  <a-layout class="basic-layout">
    <a-layout-sider
      v-model:collapsed="appStore.collapsed"
      :trigger="null"
      collapsible
      class="sidebar-container"
      width="200"
    >
      <Sidebar ref="sidebarRef" />
    </a-layout-sider>
    <a-layout>
      <a-layout-header class="header">
        <div class="header-left">
          <MenuFoldOutlined v-if="!appStore.collapsed" class="trigger" @click="appStore.toggleSidebar" />
          <MenuUnfoldOutlined v-else class="trigger" @click="appStore.toggleSidebar" />
        </div>

        <!-- 全局公司选择器 -->
        <div class="header-center">
          <a-select
            v-model:value="selectedStock"
            show-search
            placeholder="搜索公司..."
            :filter-option="false"
            :not-found-content="null"
            :dropdown-match-select-width="false"
            class="stock-selector"
            @search="handleSearch"
            @change="handleStockChange"
            @focus="handleFocus"
          >
            <a-select-option v-for="s in searchResults" :key="s.stock_code" :value="s.stock_code">
              <div class="stock-option">
                <span class="s-name">{{ s.stock_name }}</span>
                <span class="s-code">{{ s.stock_code }}</span>
              </div>
            </a-select-option>
          </a-select>
        </div>

        <div class="header-right">
          <a-dropdown>
            <a-avatar class="avatar">
              <template #icon><UserOutlined /></template>
            </a-avatar>
            <template #overlay>
              <a-menu>
                <a-menu-item key="username">
                  <UserOutlined /> {{ authStore.userInfo?.username || 'User' }}
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item key="logout" @click="handleLogout">
                  <LogoutOutlined /> 退出登录
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <a-layout-content class="content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { MenuFoldOutlined, MenuUnfoldOutlined, UserOutlined, LogoutOutlined } from '@ant-design/icons-vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { searchStocks } from '@/api/stock'
import Sidebar from './Sidebar.vue'

const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()
const sidebarRef = ref<InstanceType<typeof Sidebar> | null>(null)

const selectedStock = ref<string | undefined>()
const searchResults = ref<any[]>([])

const handleSearch = async (value: string) => {
  if (!value) {
    searchResults.value = []
    return
  }
  try {
    const res = await searchStocks({ keyword: value, page: 1, page_size: 20 })
    if (res.data.code === 200) {
      searchResults.value = res.data.data.items || []
    }
  } catch (e) {
    console.error(e)
  }
}

const handleFocus = async () => {
  if (searchResults.value.length === 0) {
    try {
      const res = await searchStocks({ keyword: '', page: 1, page_size: 20 })
      if (res.data.code === 200) {
        searchResults.value = res.data.data.items || []
      }
    } catch (e) {
      console.error(e)
    }
  }
}

const handleStockChange = (code: string) => {
  router.push(`/stock/${code}`)
  selectedStock.value = undefined
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.basic-layout {
  min-height: 100vh;
}

.sidebar-container {
  background: #001529;
}

.header {
  background: #fff;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.header-center {
  flex: 1;
  max-width: 480px;
}

.stock-selector {
  width: 100%;
}

.stock-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.s-name {
  font-weight: 500;
}

.s-code {
  color: #999;
  font-size: 12px;
  font-family: 'SF Mono', 'Consolas', monospace;
}

.header-right {
  margin-left: auto;
}

.trigger {
  font-size: 18px;
  cursor: pointer;
  color: #333;
}

.avatar {
  cursor: pointer;
  background: #1890ff;
}

.content {
  padding: 0;
  background: #f0f2f5;
  min-height: calc(100vh - 64px);
}
</style>
