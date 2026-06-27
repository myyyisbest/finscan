<template>
  <a-layout class="basic-layout" :class="{ 'mobile-layout': isMobile }">
    <!-- 桌面端侧边栏 -->
    <a-layout-sider
      v-if="!isMobile"
      v-model:collapsed="appStore.collapsed"
      :trigger="null"
      collapsible
      class="sidebar-container"
    >
      <Sidebar />
    </a-layout-sider>

    <!-- 移动端抽屉菜单 -->
    <a-drawer
      v-if="isMobile"
      v-model:open="mobileMenuOpen"
      placement="left"
      :width="260"
      :closable="false"
      class="mobile-drawer"
      @close="mobileMenuOpen = false"
    >
      <Sidebar @navigate="mobileMenuOpen = false" />
    </a-drawer>

    <a-layout>
      <a-layout-header class="header">
        <div class="header-left">
          <MenuFoldOutlined v-if="!isMobile && !appStore.collapsed" class="trigger" @click="appStore.toggleSidebar" />
          <MenuUnfoldOutlined v-else-if="!isMobile && appStore.collapsed" class="trigger" @click="appStore.toggleSidebar" />
          <MenuOutlined v-if="isMobile" class="trigger mobile-menu-btn" @click="mobileMenuOpen = true" />
          <span class="logo">FinScan</span>
        </div>
        <div class="header-center" v-if="!isMobile">
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
      <a-layout-content class="content" :class="{ 'content-mobile': isMobile }">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { MenuFoldOutlined, MenuUnfoldOutlined, MenuOutlined, UserOutlined, LogoutOutlined } from '@ant-design/icons-vue'
import Sidebar from './Sidebar.vue'
import GlobalSearch from '@/components/GlobalSearch.vue'

const appStore = useAppStore()
const authStore = useAuthStore()
const router = useRouter()
const mobileMenuOpen = ref(false)
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value < 768)

function handleResize() {
  windowWidth.value = window.innerWidth
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.basic-layout {
  min-height: 100vh;
  min-height: 100dvh; /* 动态视口高度，适配移动端 */
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
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  height: 56px;
  line-height: 56px;
  /* iOS 安全区域 */
  padding-top: env(safe-area-inset-top, 0);
  padding-left: env(safe-area-inset-left, 16px);
  padding-right: env(safe-area-inset-right, 16px);
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
  padding: 8px;
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
  min-height: calc(100vh - 56px - 32px);
  min-height: calc(100dvh - 56px - 32px);
}

.content-mobile {
  margin: 0;
  padding: 12px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 0));
  min-height: calc(100dvh - 56px);
  overflow-x: hidden;
}

/* 移动端适配 */
.mobile-layout :deep(.ant-layout-sider) {
  display: none;
}

.mobile-drawer :deep(.ant-drawer-body) {
  padding: 0;
  background: #001529;
}

.mobile-menu-btn {
  font-size: 20px;
}

@media (max-width: 767px) {
  .header {
    padding: 0 12px;
    padding-top: env(safe-area-inset-top, 0);
  }

  .logo {
    font-size: 16px;
  }
}

/* 19.5:9 窄屏适配 */
@media (max-width: 400px) {
  .header {
    height: 50px;
    line-height: 50px;
  }

  .content-mobile {
    padding: 8px;
    padding-bottom: calc(8px + env(safe-area-inset-bottom, 20px));
  }
}
</style>
