<template>
  <div class="main-layout">
    <!-- 顶部条 -->
    <header class="top-bar">
      <div class="top-bar-inner">
        <div class="logo-area" @click="$router.push('/')" style="cursor: pointer;">
          <span class="logo-text">FinScan</span>
          <span class="logo-sub">财务分析</span>
        </div>

    <!-- 主体区域 -->
        <div class="user-area">
          <span class="user-name">{{ authStore.username }}</span>
          <button class="logout-btn" @click="handleLogout">退出</button>
        </div>
      </div>
    </header>

    <!-- 主体区域 -->
    <div class="body-area">
      <!-- 左侧导航 -->
      <aside class="sidebar">
        <nav class="nav-menu">
          <router-link to="/" class="nav-item" :class="{ active: route.path === '/' }">
            <span class="nav-icon">📊</span>
            <span class="nav-text">我的自选</span>
          </router-link>
          <router-link to="/analysis" class="nav-item" :class="{ active: route.path.startsWith('/analysis') || route.path.startsWith('/stock/') }">
            <span class="nav-icon">📈</span>
            <span class="nav-text">财报分析</span>
          </router-link>
          <router-link to="/compare" class="nav-item" :class="{ active: route.path === '/compare' }">
            <span class="nav-icon">📋</span>
            <span class="nav-text">多标对比</span>
          </router-link>
          <router-link to="/finscan" class="nav-item" :class="{ active: route.path === '/finscan' }">
            <span class="nav-icon">⚠️</span>
            <span class="nav-text">财报排雷</span>
          </router-link>
          <router-link to="/announcements" class="nav-item" :class="{ active: route.path === '/announcements' }">
            <span class="nav-icon">📢</span>
            <span class="nav-text">新闻公告</span>
          </router-link>
        </nav>
      </aside>

      <!-- 主内容区 -->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

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
  max-width: 1600px;
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

/* 主体区域 */
.body-area {
  display: flex;
  max-width: 1600px;
  margin: 0 auto;
  min-height: calc(100vh - 56px);
}

/* 左侧导航 */
.sidebar {
  width: 200px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  padding: 16px 0;
  flex-shrink: 0;
}

.nav-menu {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: #333;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: #f0f7ff;
  color: #1d4ed8;
}

.nav-item.active {
  background: #e6f0ff;
  color: #1d4ed8;
  border-left-color: #1d4ed8;
  font-weight: 600;
}

.nav-icon {
  font-size: 18px;
}

/* 主内容区 */
.main-content {
  flex: 1;
  padding: 20px 24px;
  min-width: 0;
}
</style>
