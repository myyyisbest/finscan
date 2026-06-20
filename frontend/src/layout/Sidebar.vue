<template>
  <div class="sidebar">
    <div class="logo-area">
      <span v-if="!collapsed" class="logo-icon">F</span>
      <span v-if="!collapsed" class="logo-text">FinScan</span>
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
        <span>首页</span>
      </a-menu-item>
      <a-menu-item key="/">
        <template #icon>
          <SearchOutlined />
        </template>
        <span>股票检索</span>
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
        <span>风险排雷</span>
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

const router = useRouter()
const route = useRoute()
const selectedKeys = ref<string[]>([route.path])

watch(() => route.path, (newPath) => {
  selectedKeys.value = [newPath]
})

const handleMenuClick = ({ key }: { key: string }) => {
  router.push(key)
}

const collapsed = ref(false)
</script>

<style scoped>
.sidebar {
  height: 100%;
}

.logo-area {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
}

.logo-img {
  width: 32px;
  height: 32px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
}
</style>
