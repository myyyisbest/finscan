<template>
  <a-layout class="basic-layout">
    <a-layout-sider
      v-model:collapsed="appStore.collapsed"
      :trigger="null"
      collapsible
      class="sidebar-container"
    >
      <Sidebar />
    </a-layout-sider>
    <a-layout>
      <a-layout-header class="header">
        <div class="header-left">
          <MenuFoldOutlined v-if="!appStore.collapsed" class="trigger" @click="appStore.toggleSidebar" />
          <MenuUnfoldOutlined v-else class="trigger" @click="appStore.toggleSidebar" />
          <span class="logo">FinScan</span>
        </div>
        <div class="header-center">
          <GlobalSearch />
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
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { MenuFoldOutlined, MenuUnfoldOutlined, UserOutlined, LogoutOutlined } from '@ant-design/icons-vue'
import Sidebar from './Sidebar.vue'
import GlobalSearch from '@/components/GlobalSearch.vue'

const appStore = useAppStore()
const authStore = useAuthStore()
const router = useRouter()

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
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.trigger {
  font-size: 18px;
  cursor: pointer;
  color: #666;
}

.trigger:hover {
  color: #165DFF;
}

.logo {
  font-size: 18px;
  font-weight: 600;
  color: #165DFF;
}

.header-center {
  flex: 1;
  max-width: 400px;
  margin: 0 24px;
}

.header-right {
  display: flex;
  align-items: center;
}

.avatar {
  cursor: pointer;
  background: #165DFF;
}

.content {
  margin: 16px;
  min-height: calc(100vh - 64px - 32px);
}
</style>
