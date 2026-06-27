<template>
  <div class="sidebar">
    <div class="logo-area">
      <span class="logo-icon">📊</span>
      <span class="logo-text">FinScan</span>
    </div>
    <a-menu
      v-model:selectedKeys="selectedKeys"
      theme="dark"
      mode="inline"
      @click="handleMenuClick"
    >
      <a-menu-item key="/">
        <template #icon>
          <HomeOutlined />
        </template>
        <span>我的自选</span>
      </a-menu-item>
      <a-menu-item key="/analysis">
        <template #icon>
          <SearchOutlined />
        </template>
        <span>财报分析</span>
      </a-menu-item>
      <a-menu-item key="/compare">
        <template #icon>
          <BarChartOutlined />
        </template>
        <span>对标分析</span>
      </a-menu-item>
      <a-menu-item key="/risk">
        <template #icon>
          <SafetyCertificateOutlined />
        </template>
        <span>财报排雷</span>
      </a-menu-item>
      <a-menu-item key="/announcement">
        <template #icon>
          <FileTextOutlined />
        </template>
        <span>公告中心</span>
      </a-menu-item>
    </a-menu>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { HomeOutlined, SearchOutlined, BarChartOutlined, SafetyCertificateOutlined, FileTextOutlined } from '@ant-design/icons-vue'

const emit = defineEmits(['navigate'])
const router = useRouter()
const route = useRoute()
const selectedKeys = ref<string[]>([route.path])

watch(() => route.path, (newPath) => {
  selectedKeys.value = [newPath]
})

const handleMenuClick = ({ key }: { key: string }) => {
  router.push(key)
  emit('navigate')
}
</script>

<style scoped>
.sidebar {
  height: 100%;
}

.logo-area {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

:deep(.ant-menu-dark) {
  background: transparent;
}
</style>
