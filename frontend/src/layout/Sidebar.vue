<template>
  <div class="sidebar">
    <div class="logo-area">
      <span v-if="!appStore.collapsed" class="logo-text">FinScan</span>
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
      <a-menu-item key="/compare">
        <template #icon>
          <BarChartOutlined />
        </template>
        <span>公司对比</span>
      </a-menu-item>
      <a-menu-item key="/announcement">
        <template #icon>
          <FileTextOutlined />
        </template>
        <span>公告信息</span>
      </a-menu-item>
    </a-menu>

    <!-- 自选分组 -->
    <div class="watchlist-section">
      <div class="section-label" v-if="!appStore.collapsed">
        <FolderOutlined /> 自选分组
        <a-button type="link" size="small" @click="handleCreateGroup">
          <PlusOutlined />
        </a-button>
      </div>
      <a-menu
        v-if="groups.length > 0"
        v-model:selectedKeys="selectedGroupKeys"
        theme="dark"
        mode="inline"
        @click="handleGroupClick"
      >
        <a-menu-item
          v-for="group in groups"
          :key="'group_' + group.group_name"
        >
          <template #icon><FolderOpenOutlined /></template>
          <span class="group-name">{{ group.group_name }}</span>
          <span class="group-count">{{ group.stocks.length }}</span>
        </a-menu-item>
      </a-menu>
      <div v-else-if="!appStore.collapsed" class="empty-tip">
        暂无自选股票
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  HomeOutlined,
  BarChartOutlined,
  FileTextOutlined,
  FolderOutlined,
  FolderOpenOutlined,
  PlusOutlined,
} from '@ant-design/icons-vue'
import { useAppStore } from '@/stores/app'
import { getWatchlistGroups, createGroup } from '@/api/watchlist'
import { message } from 'ant-design-vue'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const selectedKeys = ref<string[]>([route.path])
const selectedGroupKeys = ref<string[]>([])
const groups = ref<any[]>([])

watch(() => route.path, (newPath) => {
  selectedKeys.value = [newPath]
})

const handleMenuClick = ({ key }: { key: string }) => {
  router.push(key)
}

const handleGroupClick = ({ key }: { key: string }) => {
  const groupName = key.replace('group_', '')
  router.push({ path: '/', query: { group: groupName } })
}

const handleCreateGroup = async () => {
  const name = prompt('请输入分组名称:')
  if (!name) return
  try {
    await createGroup({ group_name: name })
    message.success('创建成功')
    loadGroups()
  } catch {
    message.error('创建失败')
  }
}

const loadGroups = async () => {
  try {
    const res = await getWatchlistGroups()
    if (res.data.code === 200) {
      groups.value = res.data.data.groups || []
    }
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadGroups()
})

// 暴露给父组件刷新
defineExpose({ loadGroups })
</script>

<style scoped>
.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.logo-area {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
}

.watchlist-section {
  flex: 1;
  overflow-y: auto;
  border-top: 1px solid rgba(255,255,255,0.1);
  margin-top: 8px;
}

.section-label {
  padding: 8px 20px 4px;
  color: rgba(255,255,255,0.45);
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.section-label .ant-btn {
  color: rgba(255,255,255,0.45);
  padding: 0;
  height: auto;
}

.group-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-count {
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  background: rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 0 6px;
  line-height: 16px;
}

.empty-tip {
  padding: 8px 20px;
  color: rgba(255,255,255,0.25);
  font-size: 12px;
}
</style>
