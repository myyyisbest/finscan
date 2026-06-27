<template>
  <div class="home-page">
    <!-- 顶部：分组卡片 + 操作按钮 -->
    <div class="page-header">
      <div class="group-cards">
        <div
          class="group-card"
          :class="{ active: activeGroupKey === 'all' }"
          @click="switchToGroup('all')"
        >
          <div class="group-card-name">全部</div>
          <div class="group-card-count">{{ totalStockCount }}</div>
        </div>
        <div
          v-for="g in groups.filter(x => x.id !== 0)"
          :key="g.id"
          class="group-card"
          :class="{ active: activeGroupKey === String(g.id) }"
          @click="switchToGroup(String(g.id))"
        >
          <div class="group-card-name">
            <span class="group-dot" :style="{ background: getGroupColor(g.id) }"></span>
            {{ g.name }}
          </div>
          <div class="group-card-count">{{ g.stock_count }}</div>
        </div>
        <div class="group-card add-group-card" @click="showAddGroupModal = true">
          <PlusOutlined style="font-size: 20px; color: #999;" />
        </div>
      </div>
      <div class="header-actions">
        <a-button type="primary" @click="refreshData" :loading="loading">
          <ReloadOutlined /> 刷新
        </a-button>
        <a-button @click="collectAll" :loading="collecting">
          <CloudDownloadOutlined /> 采集
        </a-button>
      </div>
    </div>

    <!-- 分组统计卡片 -->
    <div class="summary-cards">
      <a-card size="small" class="summary-card">
        <a-statistic title="股票数量" :value="watchlist.length" />
      </a-card>
      <a-card size="small" class="summary-card">
        <a-statistic title="已采集" :value="watchlist.filter(w => w.latest_report).length" />
      </a-card>
      <a-card size="small" class="summary-card">
        <a-statistic title="平均ROE" :value="avgRoe" :precision="2" suffix="%" />
      </a-card>
      <a-card size="small" class="summary-card">
        <a-statistic title="平均资产负债率" :value="avgDebtRatio" :precision="2" suffix="%" />
      </a-card>
    </div>

    <a-card class="watchlist-card">
      <template #title>
        <span>{{ activeGroupKey === 'all' ? '全部股票' : (groups.find(g => String(g.id) === activeGroupKey)?.name || '分组') }}</span>
      </template>
      <template #extra>
        <a-button v-if="activeGroupKey !== 'all'" type="text" danger size="small" @click="deleteCurrentGroup">
          <DeleteOutlined /> 删除分组
        </a-button>
      </template>
      <a-spin :spinning="loading">
        <a-table
          :columns="columns"
          :data-source="watchlist"
          :pagination="{ pageSize: 20 }"
          row-key="stock_code"
          :scroll="{ x: 1200 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'group_name'">
              <span class="group-tag" :style="{ background: getGroupColor(record.group_id || 0) }">
                {{ record.group_name }}
              </span>
            </template>
            <template v-else-if="column.key === 'stock_name'">
              <a @click="goToStock(record.stock_code)" class="stock-link">
                <span class="stock-code">{{ record.stock_code }}</span>
                <span class="stock-name-text">{{ record.stock_name }}</span>
              </a>
            </template>
            <template v-else-if="column.key === 'action'">
              <div class="action-btns">
                <a-button type="link" size="small" @click.stop="collectStock(record)" :loading="collectingMap[record.stock_code]">
                  <CloudDownloadOutlined /> 采集
                </a-button>
                <a-button type="link" danger size="small" @click.stop="removeStock(record)">
                  移除
                </a-button>
              </div>
            </template>
            <template v-else-if="column.key === 'latest_report'">
              <span v-if="record.latest_report">{{ record.latest_report.report_name }}</span>
              <span v-else class="no-data">未采集</span>
            </template>
            <template v-else-if="column.key === 'total_revenue'">
              <span v-if="record.latest_report?.total_revenue">
                {{ formatWan(record.latest_report.total_revenue) }}
              </span>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'net_profit_parent'">
              <span v-if="record.latest_report?.net_profit_parent"
                :class="getProfitClass(record.latest_report.net_profit_parent)">
                {{ formatWan(record.latest_report.net_profit_parent) }}
              </span>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'roe'">
              <span v-if="record.latest_report?.roe != null"
                :class="getRoeClass(record.latest_report.roe)">
                {{ record.latest_report.roe?.toFixed(2) }}%
              </span>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'debt_ratio'">
              <span v-if="record.latest_report?.debt_ratio != null">
                {{ record.latest_report.debt_ratio?.toFixed(2) }}%
              </span>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'revenue_yoy'">
              <span v-if="record.latest_report?.revenue_yoy != null"
                :class="getYoyClass(record.latest_report.revenue_yoy)">
                {{ record.latest_report.revenue_yoy?.toFixed(2) }}%
              </span>
              <span v-else>-</span>
            </template>
          </template>
        </a-table>
        <a-empty v-if="!loading && watchlist.length === 0" description="暂无自选股">
          <template #description>
            <span>暂无自选股，点击右下角按钮添加股票</span>
          </template>
        </a-empty>
      </a-spin>
    </a-card>

    <!-- 添加股票弹窗 -->
    <a-modal
      v-model:open="addModalVisible"
      title="添加自选股"
      @ok="confirmAdd"
      :confirm-loading="addLoading"
      okText="添加"
      cancelText="取消"
    >
      <div class="add-form">
        <div class="form-row">
          <div class="form-item">
            <div class="form-label">股票代码 <span class="required">*</span></div>
            <a-input v-model:value="addForm.code" placeholder="如 002130" :disabled="!!addForm.name" />
          </div>
          <div class="form-divider">或</div>
          <div class="form-item">
            <div class="form-label">股票名称 <span class="required">*</span></div>
            <a-input v-model:value="addForm.name" placeholder="如 沃尔核材" :disabled="!!addForm.code" />
          </div>
        </div>
        <div class="form-hint">代码/名称二选一填写即可</div>
        <div class="form-item">
          <div class="form-label">加入分组</div>
          <a-select v-model:value="addForm.groupId" placeholder="默认分组" style="width: 100%">
            <a-select-option :value="0">默认分组</a-select-option>
            <a-select-option v-for="g in groups.filter(x => x.id !== 0)" :key="g.id" :value="g.id">
              {{ g.name }}
            </a-select-option>
          </a-select>
        </div>
      </div>
    </a-modal>

    <!-- 新建分组弹窗 -->
    <a-modal
      v-model:open="showAddGroupModal"
      title="新建分组"
      @ok="confirmAddGroup"
      :confirm-loading="addGroupLoading"
      okText="创建"
      cancelText="取消"
    >
      <a-input v-model:value="newGroupName" placeholder="请输入分组名称" />
    </a-modal>

    <div class="fab-btn" @click="addModalVisible = true" title="添加自选股">
      <PlusOutlined style="font-size: 24px; color: #fff" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined, CloudDownloadOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { watchlistApi, stockApi, collectorApi, type WatchlistItem, type SearchResult } from '@/api/finance'

const router = useRouter()
const loading = ref(false)
const collecting = ref(false)
const watchlist = ref<WatchlistItem[]>([])
const collectingMap = ref<Record<string, boolean>>({})

// 分组相关
interface Group { id: number; name: string; stock_count: number }
const groups = ref<Group[]>([])
const activeGroupKey = ref('all')
const showAddGroupModal = ref(false)
const newGroupName = ref('')
const addGroupLoading = ref(false)

// 分组颜色映射
const GROUP_COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16']
function getGroupColor(groupId: number): string {
  if (groupId === 0) return '#d9d9d9'
  return GROUP_COLORS[(groupId - 1) % GROUP_COLORS.length]
}

// 总股票数
const totalStockCount = computed(() => groups.value.find(g => g.id === 0)?.stock_count || watchlist.value.length)

function switchToGroup(key: string) {
  activeGroupKey.value = key
  loadWatchlist()
}

// 添加股票表单
const addModalVisible = ref(false)
const addForm = ref({ code: '', name: '', groupId: 0 })
const addLoading = ref(false)

// 计算属性
const avgRoe = computed(() => {
  const roes = watchlist.value
    .filter(w => w.latest_report?.roe != null)
    .map(w => w.latest_report!.roe!)
  if (roes.length === 0) return 0
  return roes.reduce((a, b) => a + b, 0) / roes.length
})

const avgDebtRatio = computed(() => {
  const ratios = watchlist.value
    .filter(w => w.latest_report?.debt_ratio != null)
    .map(w => w.latest_report!.debt_ratio!)
  if (ratios.length === 0) return 0
  return ratios.reduce((a, b) => a + b, 0) / ratios.length
})

const columns = [
  { title: '分组', key: 'group_name', width: 90 },
  { title: '股票', key: 'stock_name', width: 160, fixed: 'left' as const },
  { title: '最新报告期', key: 'latest_report', width: 120 },
  { title: '营业总收入(万)', key: 'total_revenue', width: 150, align: 'right' as const },
  { title: '归母净利润(万)', key: 'net_profit_parent', width: 150, align: 'right' as const },
  { title: 'ROE(%)', key: 'roe', width: 100, align: 'right' as const },
  { title: '资产负债率(%)', key: 'debt_ratio', width: 120, align: 'right' as const },
  { title: '营收同比(%)', key: 'revenue_yoy', width: 120, align: 'right' as const },
  { title: '操作', key: 'action', width: 80, align: 'center' as const, fixed: 'right' as const },
]

async function loadGroups() {
  try {
    const res = await watchlistApi.listGroups()
    if (res.code === 0) {
      groups.value = res.data || []
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadWatchlist() {
  loading.value = true
  try {
    const groupId = activeGroupKey.value === 'all' ? null : parseInt(activeGroupKey.value)
    const res = await watchlistApi.list(groupId ?? undefined)
    if (res.code === 0) {
      watchlist.value = res.data || []
    }
  } catch (e) {
    console.error(e)
    message.error('加载自选股失败')
  } finally {
    loading.value = false
  }
}

async function confirmAddGroup() {
  if (!newGroupName.value.trim()) {
    message.warning('请输入分组名称')
    return
  }
  addGroupLoading.value = true
  try {
    await watchlistApi.createGroup(newGroupName.value.trim())
    message.success('分组创建成功')
    showAddGroupModal.value = false
    newGroupName.value = ''
    await loadGroups()
    // 切换到新建的分组
    const g = groups.value.find(x => x.name === newGroupName.value.trim())
    if (g) activeGroupKey.value = String(g.id)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '创建失败')
  } finally {
    addGroupLoading.value = false
  }
}

async function deleteCurrentGroup() {
  const groupId = parseInt(activeGroupKey.value)
  try {
    await watchlistApi.deleteGroup(groupId)
    message.success('分组已删除')
    await loadGroups()
    activeGroupKey.value = 'all'
    loadWatchlist()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '删除失败')
  }
}

function formatWan(val: number) {
  if (val == null) return '-'
  const absVal = Math.abs(val)
  if (absVal >= 1e8) return (val / 1e8).toFixed(2) + '亿'
  if (absVal >= 1e4) return (val / 1e4).toFixed(2) + '万'
  return val.toFixed(2)
}

function getProfitClass(val: number) {
  return val >= 0 ? 'profit-pos' : 'profit-neg'
}

function getRoeClass(val: number) {
  if (val >= 15) return 'roe-good'
  if (val >= 8) return 'roe-ok'
  return 'roe-bad'
}

function getYoyClass(val: number) {
  return val >= 0 ? 'profit-pos' : 'profit-neg'
}

function goToStock(code: string) {
  router.push(`/stock/${code}/main-indicators`)
}

async function removeStock(record: WatchlistItem) {
  try {
    await watchlistApi.remove(record.stock_code)
    message.success('已移除')
    loadWatchlist()
    loadGroups()
  } catch (e) {
    message.error('移除失败')
  }
}

async function refreshData() {
  await loadWatchlist()
  message.success('已刷新')
}

async function collectAll() {
  collecting.value = true
  try {
    await collectorApi.triggerCollect('watchlist')
    message.success('采集任务已启动，请稍候刷新查看')
    setTimeout(() => { loadWatchlist() }, 5000)
  } catch (e) {
    message.error('启动采集失败')
  } finally {
    collecting.value = false
  }
}

async function collectStock(record: WatchlistItem) {
  if (collectingMap.value[record.stock_code]) return
  collectingMap.value[record.stock_code] = true
  try {
    await collectorApi.triggerCollect('single', record.stock_code)
    message.success(`已开始采集 ${record.stock_name}，请稍候刷新查看`)
    setTimeout(() => {
      loadWatchlist()
      collectingMap.value[record.stock_code] = false
    }, 8000)
  } catch (e) {
    message.error('启动采集失败')
    collectingMap.value[record.stock_code] = false
  }
}

async function confirmAdd() {
  const { code, name, groupId } = addForm.value
  if (!code && !name) {
    message.warning('请填写股票代码或名称')
    return
  }

  addLoading.value = true
  try {
    const res = await watchlistApi.add(code || name, undefined, groupId || 0)
    if (res.code === 0) {
      message.success('添加成功，可点击"采集"按钮获取财务数据')
      addModalVisible.value = false
      addForm.value = { code: '', name: '', groupId: 0 }
      loadWatchlist()
      loadGroups()
    } else {
      message.error(res.message || '添加失败')
    }
  } catch (e: any) {
    message.error(e?.response?.data?.message || '添加失败')
  } finally {
    addLoading.value = false
  }
}

onMounted(() => {
  loadGroups()
  loadWatchlist()
})
</script>

<style scoped>
.home-page { min-height: calc(100vh - 96px); }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 16px;
}

.group-cards {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  flex: 1;
}

.group-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 90px;
  height: 64px;
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  padding: 8px 16px;
}
.group-card:hover {
  border-color: #1d4ed8;
  background: #f0f5ff;
}
.group-card.active {
  border-color: #1d4ed8;
  background: #e6f4ff;
}
.group-card-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  display: flex;
  align-items: center;
  gap: 6px;
}
.group-card-count {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.group-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.add-group-card {
  border-style: dashed;
  color: #999;
}
.add-group-card:hover {
  color: #1d4ed8;
}

.header-actions { display: flex; gap: 12px; flex-shrink: 0; }

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.summary-card { background: #fafafa; }

.watchlist-card { background: #fff; border-radius: 8px; }

.stock-link { display: flex; flex-direction: column; gap: 2px; cursor: pointer; }
.stock-link:hover .stock-name-text { color: #1d4ed8; }
.stock-code { font-size: 12px; color: #999; }
.stock-name-text { font-size: 14px; font-weight: 500; color: #1a1a1a; }
.group-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #fff;
}
.no-data { color: #ccc; }

.profit-pos { color: #cf1322; }
.profit-neg { color: #389e0d; }
.roe-good { color: #cf1322; font-weight: 600; }
.roe-ok { color: #d48806; }
.roe-bad { color: #389e0d; }

.action-btns { display: flex; gap: 4px; align-items: center; justify-content: center; }

.add-form { display: flex; flex-direction: column; gap: 16px; }
.form-row { display: flex; align-items: flex-end; gap: 8px; }
.form-item { flex: 1; }
.form-divider { color: #999; padding-bottom: 6px; }
.form-label { font-size: 13px; color: #333; margin-bottom: 6px; }
.required { color: #cf1322; }
.form-hint { font-size: 12px; color: #999; margin-top: -10px; }

.fab-btn {
  position: fixed;
  right: 32px;
  bottom: 32px;
  width: 52px;
  height: 52px;
  background: #1d4ed8;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.4);
  transition: transform 0.2s;
  z-index: 100;
}
.fab-btn:hover { transform: scale(1.08); }
</style>
