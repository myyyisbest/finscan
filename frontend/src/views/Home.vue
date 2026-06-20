<template>
  <div class="home-page">
    <div class="search-section">
      <h2 class="section-title">搜索股票</h2>
      <GlobalSearch />
    </div>

    <div class="stats-section">
      <a-row :gutter="16">
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="自选股数量"
              :value="totalStocks"
              :value-style="{ color: '#165DFF' }"
            />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="低风险"
              :value="riskStats.low"
              :value-style="{ color: '#52c41a' }"
            />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="中风险"
              :value="riskStats.medium"
              :value-style="{ color: '#faad14' }"
            />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="高风险"
              :value="riskStats.high"
              :value-style="{ color: '#ff4d4f' }"
            />
          </a-card>
        </a-col>
      </a-row>
    </div>

    <div class="watchlist-section">
      <a-row :gutter="16">
        <a-col :span="6">
          <a-card class="group-list-card" title="自选分组">
            <template #extra>
              <a-button type="link" size="small" @click="showCreateGroupModal">
                <PlusOutlined /> 新建分组
              </a-button>
            </template>
            <a-list item-layout="horizontal" :data-source="groups">
              <template #renderItem="{ item }">
                <a-list-item
                  :class="{ 'active-group': selectedGroup === item.group_name }"
                  @click="selectGroup(item.group_name)"
                >
                  <a-list-item-meta>
                    <template #title>
                      <FolderOutlined /> {{ item.group_name }}
                    </template>
                    <template #description>
                      {{ item.stocks.length }} 只股票
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </a-col>
        <a-col :span="18">
          <a-card class="stock-list-card">
            <template #title>
              <div class="stock-list-header">
                <span>{{ selectedGroup || '全部自选' }}</span>
                <a-button type="primary" size="small" @click="showAddStockModal">
                  <PlusOutlined /> 添加股票
                </a-button>
              </div>
            </template>
            <a-spin :spinning="loading">
              <a-row :gutter="[16, 16]">
                <a-col
                  v-for="stock in currentStocks"
                  :key="stock.stock_code"
                  :span="8"
                >
                  <StockCard :stock="stock" />
                </a-col>
              </a-row>
              <a-empty v-if="!loading && currentStocks.length === 0" description="暂无股票" />
            </a-spin>
          </a-card>
        </a-col>
      </a-row>
    </div>

    <a-modal
      v-model:open="addStockModalVisible"
      title="添加股票"
      @ok="handleAddStock"
      :confirm-loading="addStockLoading"
    >
      <GlobalSearch @select="handleStockSelect" />
      <a-divider />
      <a-form :model="addStockForm" layout="vertical">
        <a-form-item label="分组" name="group_name">
          <a-select v-model:value="addStockForm.group_name" placeholder="选择分组">
            <a-select-option v-for="group in groups" :key="group.group_name" :value="group.group_name">
              {{ group.group_name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="备注" name="remark">
          <a-input v-model:value="addStockForm.remark" placeholder="添加备注 (可选)" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="createGroupModalVisible"
      title="新建分组"
      @ok="handleCreateGroup"
      :confirm-loading="createGroupLoading"
    >
      <a-form :model="newGroupForm" layout="vertical">
        <a-form-item label="分组名称" name="group_name" :rules="[{ required: true, message: '请输入分组名称' }]">
          <a-input v-model:value="newGroupForm.group_name" placeholder="输入分组名称" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, FolderOutlined } from '@ant-design/icons-vue'
import GlobalSearch from '@/components/GlobalSearch.vue'
import StockCard from '@/components/StockCard.vue'
import { getWatchlistGroups, addToWatchlist, createGroup } from '@/api/watchlist'
import type { WatchlistGroup, StockSearchItem } from '@/types'

const loading = ref(false)
const groups = ref<WatchlistGroup[]>([])
const selectedGroup = ref<string | null>(null)

const addStockModalVisible = ref(false)
const addStockLoading = ref(false)
const selectedStock = ref<StockSearchItem | null>(null)
const addStockForm = ref({
  group_name: '',
  remark: ''
})

const createGroupModalVisible = ref(false)
const createGroupLoading = ref(false)
const newGroupForm = ref({
  group_name: ''
})

const totalStocks = computed(() => {
  return groups.value.reduce((sum, g) => sum + g.stocks.length, 0)
})

const riskStats = computed(() => {
  return { low: 0, medium: 0, high: 0 }
})

const currentStocks = computed(() => {
  if (!selectedGroup.value) {
    return groups.value.flatMap(g => g.stocks.map(s => ({
      stock_code: s.stock_code,
      stock_name: s.stock_name,
      is_st: false,
      industry: null,
      market: null
    })))
  }
  const group = groups.value.find(g => g.group_name === selectedGroup.value)
  if (!group) return []
  return group.stocks.map(s => ({
    stock_code: s.stock_code,
    stock_name: s.stock_name,
    is_st: false,
    industry: null,
    market: null
  }))
})

const loadGroups = async () => {
  loading.value = true
  try {
    const response = await getWatchlistGroups()
    if (response.data.code === 200) {
      groups.value = response.data.data || []
      if (groups.value.length > 0 && !selectedGroup.value) {
        selectedGroup.value = groups.value[0].group_name
      }
    }
  } catch (error) {
    console.error('Failed to load groups:', error)
  } finally {
    loading.value = false
  }
}

const selectGroup = (groupName: string) => {
  selectedGroup.value = groupName
}

const showAddStockModal = () => {
  addStockModalVisible.value = true
  selectedStock.value = null
  addStockForm.value = { group_name: selectedGroup.value || '', remark: '' }
}

const handleStockSelect = (stockCode: string) => {
  selectedStock.value = {
    stock_code: stockCode,
    stock_name: stockCode,
    is_st: false,
    industry: null,
    market: null
  }
}

const handleAddStock = async () => {
  if (!selectedStock.value) {
    message.warning('请先搜索选择股票')
    return
  }
  if (!addStockForm.value.group_name) {
    message.warning('请选择分组')
    return
  }

  addStockLoading.value = true
  try {
    await addToWatchlist({
      stock_code: selectedStock.value.stock_code,
      stock_name: selectedStock.value.stock_name,
      group_name: addStockForm.value.group_name,
      remark: addStockForm.value.remark
    })
    message.success('添加成功')
    addStockModalVisible.value = false
    loadGroups()
  } catch (error) {
    message.error('添加失败')
  } finally {
    addStockLoading.value = false
  }
}

const showCreateGroupModal = () => {
  createGroupModalVisible.value = true
  newGroupForm.value.group_name = ''
}

const handleCreateGroup = async () => {
  if (!newGroupForm.value.group_name) {
    message.warning('请输入分组名称')
    return
  }

  createGroupLoading.value = true
  try {
    await createGroup({ group_name: newGroupForm.value.group_name })
    message.success('创建成功')
    createGroupModalVisible.value = false
    loadGroups()
  } catch (error) {
    message.error('创建失败')
  } finally {
    createGroupLoading.value = false
  }
}

onMounted(() => {
  loadGroups()
})
</script>

<style scoped>
.home-page {
  padding: 16px;
}

.search-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 12px;
  color: #333;
}

.stats-section {
  margin-bottom: 24px;
}

.stat-card {
  text-align: center;
}

.watchlist-section {
  margin-bottom: 24px;
}

.group-list-card {
  height: fit-content;
}

.stock-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.active-group {
  background-color: #e6f7ff;
  border-radius: 4px;
}

:deep(.ant-list-item) {
  cursor: pointer;
  padding: 8px 12px;
}

:deep(.ant-list-item:hover) {
  background-color: #f5f5f5;
}
</style>
