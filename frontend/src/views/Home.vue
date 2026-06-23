<template>
  <div class="home-page">
    <!-- 欢迎 + 快捷统计 -->
    <a-row :gutter="16" class="stat-row">
      <a-col :span="6">
        <a-card class="stat-card" hoverable>
          <a-statistic title="自选股票" :value="totalStocks" :value-style="{ color: '#165DFF' }">
            <template #suffix>只</template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card" hoverable>
          <a-statistic title="分组数量" :value="groups.length" :value-style="{ color: '#722ED1' }">
            <template #suffix>个</template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card" hoverable>
          <a-statistic title="近期公告" :value="recentAnnouncements.length" :value-style="{ color: '#13C2C2' }">
            <template #suffix>条</template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card" hoverable>
          <a-statistic title="风险股" :value="riskStocks" :value-style="{ color: '#F5222D' }">
            <template #suffix>只</template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16">
      <!-- 自选股列表 -->
      <a-col :span="14">
        <a-card title="我的自选" :bordered="false" class="main-card">
          <template #extra>
            <a-space>
              <a-select v-model:value="selectedGroup" placeholder="选择分组" style="width: 120px" allow-clear>
                <a-select-option v-for="g in groups" :key="g.group_name" :value="g.group_name">
                  {{ g.group_name }} ({{ g.stocks.length }})
                </a-select-option>
              </a-select>
              <a-button type="primary" size="small" @click="showAddModal = true">
                <PlusOutlined /> 添加
              </a-button>
            </a-space>
          </template>

          <a-spin :spinning="loading">
            <a-row :gutter="[12, 12]">
              <a-col v-for="stock in displayStocks" :key="stock.stock_code" :span="8">
                <a-card
                  size="small"
                  class="stock-mini-card"
                  hoverable
                  @click="goDetail(stock.stock_code)"
                >
                  <div class="mini-header">
                    <span class="mini-name">{{ stock.stock_name }}</span>
                    <a-tag v-if="stock.is_st" color="red" size="small">ST</a-tag>
                  </div>
                  <div class="mini-code">{{ stock.stock_code }}</div>
                </a-card>
              </a-col>
              <a-col v-if="displayStocks.length === 0 && !loading" :span="24">
                <a-empty description="该分组暂无股票,点击右上角添加">
                  <a-button type="primary" @click="showAddModal = true">添加股票</a-button>
                </a-empty>
              </a-col>
            </a-row>
          </a-spin>
        </a-card>
      </a-col>

      <!-- 近期公告 -->
      <a-col :span="10">
        <a-card title="近期公告" :bordered="false" class="main-card">
          <template #extra>
            <a-button type="link" size="small" @click="$router.push('/announcement')">
              查看全部
            </a-button>
          </template>

          <a-spin :spinning="annLoading">
            <a-list size="small" :data-source="recentAnnouncements" :loading="annLoading">
              <template #renderItem="{ item }">
                <a-list-item class="ann-item" @click="goAnnouncement(item)">
                  <a-list-item-meta>
                    <template #title>
                      <a-badge v-if="item.is_risk" status="error" text="风险" />
                      {{ item.ann_title }}
                    </template>
                    <template #description>
                      <a-space>
                        <span class="ann-stock">{{ item.stock_code }}</span>
                        <span>{{ item.ann_type }}</span>
                        <span>{{ item.publish_date }}</span>
                      </a-space>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
            <a-empty v-if="recentAnnouncements.length === 0 && !annLoading" description="暂无公告数据" />
          </a-spin>
        </a-card>
      </a-col>
    </a-row>

    <!-- 添加股票弹窗 -->
    <a-modal v-model:open="showAddModal" title="添加自选股票" @ok="handleAddStock" :confirm-loading="addLoading">
      <GlobalSearch no-navigate @select="handleStockSelect" style="margin-bottom: 16px" />
      <a-divider />
      <a-form :model="addForm" layout="vertical">
        <a-form-item label="分组" name="group_name">
          <a-select v-model:value="addForm.group_name" placeholder="选择或新建分组">
            <a-select-option v-for="g in groups" :key="g.group_name" :value="g.group_name">
              {{ g.group_name }}
            </a-select-option>
            <a-select-option key="__new__" value="__new__">
              <span style="color: #1890ff">+ 新建分组</span>
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="addForm.group_name === '__new__'" label="新建分组名" name="new_group_name">
          <a-input v-model:value="addForm.new_group_name" placeholder="输入分组名称" />
        </a-form-item>
        <div v-if="selectedStockItem" class="selected-stock">
          已选: <b>{{ selectedStockItem.stock_name }}</b> ({{ selectedStockItem.stock_code }})
        </div>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import GlobalSearch from '@/components/GlobalSearch.vue'
import { getWatchlistGroups, addToWatchlist as addStock, createGroup } from '@/api/watchlist'
import { getAnnouncements } from '@/api/announcement'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const groups = ref<any[]>([])
const selectedGroup = ref<string | undefined>()
const showAddModal = ref(false)
const addLoading = ref(false)
const selectedStockItem = ref<any>(null)
const addForm = ref({ group_name: '', new_group_name: '' })

const annLoading = ref(false)
const recentAnnouncements = ref<any[]>([])

const totalStocks = computed(() => groups.value.reduce((s, g) => s + g.stocks.length, 0))
const riskStocks = computed(() => 0)

const displayStocks = computed(() => {
  if (selectedGroup.value) {
    const g = groups.value.find(x => x.group_name === selectedGroup.value)
    return g ? g.stocks.map((s: any) => ({ stock_code: s.stock_code, stock_name: s.stock_name, is_st: false })) : []
  }
  return groups.value.flatMap((g: any) =>
    g.stocks.map((s: any) => ({ stock_code: s.stock_code, stock_name: s.stock_name, is_st: false }))
  )
})

const loadGroups = async () => {
  loading.value = true
  try {
    const res = await getWatchlistGroups()
    if (res.data.code === 200) {
      groups.value = res.data.data.groups || []
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const loadAnnouncements = async () => {
  annLoading.value = true
  try {
    const res = await getAnnouncements({ page: 1, page_size: 10 })
    if (res.data.code === 200) {
      recentAnnouncements.value = res.data.data.items || []
    }
  } catch (e) {
    console.error(e)
  } finally {
    annLoading.value = false
  }
}

const goDetail = (code: string) => {
  router.push(`/stock/${code}`)
}

const goAnnouncement = (item: any) => {
  router.push({ path: '/announcement', query: { stock: item.stock_code } })
}

const handleStockSelect = (item: { stock_code: string; stock_name: string }) => {
  selectedStockItem.value = item
}

const handleAddStock = async () => {
  if (!selectedStockItem.value) {
    message.warning('请先搜索并选择股票')
    return
  }
  let groupName = addForm.value.group_name
  if (groupName === '__new__') {
    if (!addForm.value.new_group_name) {
      message.warning('请输入新建分组名称')
      return
    }
    try {
      await createGroup({ group_name: addForm.value.new_group_name })
      groupName = addForm.value.new_group_name
    } catch {
      message.error('创建分组失败')
      return
    }
  }
  if (!groupName) {
    message.warning('请选择分组')
    return
  }
  addLoading.value = true
  try {
    await addStock({
      stock_code: selectedStockItem.value.stock_code,
      stock_name: selectedStockItem.value.stock_name,
      group_name: groupName,
    })
    message.success('添加成功')
    showAddModal.value = false
    loadGroups()
  } catch {
    message.error('添加失败')
  } finally {
    addLoading.value = false
  }
}

onMounted(() => {
  if (route.query.group) {
    selectedGroup.value = route.query.group as string
  }
  loadGroups()
  loadAnnouncements()
})
</script>

<style scoped>
.home-page {
  padding: 20px;
}

.stat-row {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
}

.main-card {
  height: 100%;
}

.stock-mini-card {
  cursor: pointer;
  background: #fafafa;
  transition: all 0.2s;
}

.stock-mini-card:hover {
  background: #e6f7ff;
  border-color: #1890ff;
}

.mini-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mini-name {
  font-weight: 600;
  font-size: 14px;
}

.mini-code {
  font-size: 12px;
  color: #999;
  font-family: 'SF Mono', Consolas, monospace;
  margin-top: 4px;
}

.ann-item {
  cursor: pointer;
  padding: 8px 0;
}

.ann-item:hover {
  background: #f5f5f5;
}

.ann-stock {
  font-family: 'SF Mono', Consolas, monospace;
  font-size: 12px;
  color: #1890ff;
}

.selected-stock {
  padding: 8px 12px;
  background: #e6f7ff;
  border-radius: 4px;
  color: #1890ff;
}
</style>
