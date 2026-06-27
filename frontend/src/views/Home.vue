<template>
  <div class="home-page">
    <!-- 分组卡片视图（首页） -->
    <div v-if="viewMode === 'cards'" class="group-cards-view fade-in">
      <div class="view-header">
        <div>
          <h1 class="view-title">我的自选分组</h1>
          <p class="view-subtitle">管理您的股票分组与持仓跟踪</p>
        </div>
        <div class="header-actions">
          <a-button type="primary" @click="showAddGroupModal = true">
            <PlusOutlined /> 新建分组
          </a-button>
          <a-button @click="collectAll" :loading="collecting">
            <CloudDownloadOutlined /> 采集全部
          </a-button>
        </div>
      </div>

      <div class="group-cards-grid">
        <!-- 全部公司卡片 -->
        <div class="group-card card-hover" @click="openGroupDetail('all')">
          <div class="card-gradient gradient-all"></div>
          <div class="card-content">
            <div class="card-icon icon-all">
              <AppstoreOutlined />
            </div>
            <div class="card-info">
              <h3 class="card-title">全部公司</h3>
              <p class="card-desc">查看所有自选股票</p>
              <div class="card-stats">
                <div class="stat-item">
                  <span class="stat-label">股票数</span>
                  <span class="stat-value">{{ totalCount }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">平均ROE</span>
                  <span class="stat-value">{{ allAvgRoe }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 各分组卡片 -->
        <div
          v-for="g in groups"
          :key="g.id"
          class="group-card card-hover"
          @click="openGroupDetail(String(g.id))"
        >
          <div class="card-gradient" :style="{ background: `linear-gradient(135deg, ${getGroupColor(g.id)}22 0%, ${getGroupColor(g.id)}05 100%)` }"></div>
          <div class="card-content">
            <div class="card-icon" :style="{ background: getGroupColor(g.id) }">
              <FolderOutlined />
            </div>
            <div class="card-info">
              <h3 class="card-title">{{ g.name }}</h3>
              <p class="card-desc">共 {{ g.stock_count }} 只股票</p>
              <div class="card-stats">
                <div class="stat-item">
                  <span class="stat-label">股票数</span>
                  <span class="stat-value">{{ g.stock_count }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">已采集</span>
                  <span class="stat-value">{{ getGroupCollectedCount(g.id) }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="card-actions" @click.stop>
            <a-button type="text" size="small" @click="showRenameGroup(g)">
              <EditOutlined />
            </a-button>
            <a-popconfirm
              title="确定删除该分组？组内股票将移至默认分组"
              ok-text="确定"
              cancel-text="取消"
              @confirm="deleteGroup(g.id)"
            >
              <a-button type="text" danger size="small">
                <DeleteOutlined />
              </a-button>
            </a-popconfirm>
          </div>
        </div>

        <!-- 新建分组卡片 -->
        <div class="group-card add-card" @click="showAddGroupModal = true">
          <div class="add-card-inner">
            <div class="add-icon">
              <PlusOutlined />
            </div>
            <span class="add-text">新建分组</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 分组详情（列表视图） -->
    <div v-if="viewMode === 'list'" class="group-list-view fade-in">
      <div class="list-header">
        <a-button class="back-btn" @click="backToCards">
          <ArrowLeftOutlined /> 返回
        </a-button>
        <div class="list-title-area">
          <h2 class="list-title">{{ currentGroupTitle }}</h2>
          <p class="list-subtitle">共 {{ watchlist.length }} 只股票</p>
        </div>
        <a-space>
          <a-button @click="collectAll" :loading="collecting">
            <CloudDownloadOutlined /> 采集本组
          </a-button>
          <a-button type="primary" @click="addModalVisible = true">
            <PlusOutlined /> 添加股票
          </a-button>
        </a-space>
      </div>

      <a-card class="watchlist-card">
        <a-spin :spinning="loading">
          <a-table
            :columns="columns"
            :data-source="sortedWatchlist"
            :pagination="{ pageSize: 20 }"
            row-key="stock_code"
            :scroll="{ x: 1200 }"
            size="middle"
            @change="handleTableChange"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'group_name'">
                <a-select
                  v-model:value="record.group_id"
                  size="small"
                  style="width: 100px"
                  @change="moveStockGroup(record)"
                >
                  <a-select-option :value="0">默认分组</a-select-option>
                  <a-select-option v-for="g in groups" :key="g.id" :value="g.id">
                    {{ g.name }}
                  </a-select-option>
                </a-select>
              </template>
              <template v-else-if="column.key === 'stock_name'">
                <a @click="goToStock(record.stock_code)" class="stock-link">
                  <span class="stock-code">{{ record.stock_code }}</span>
                  <span class="stock-name-text">{{ record.stock_name }}</span>
                </a>
              </template>
              <template v-else-if="column.key === 'fin_analysis'">
                <a-button type="link" size="small" @click="goToStock(record.stock_code)">
                  <LineChartOutlined /> 财报分析
                </a-button>
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
              <template v-else-if="column.key === 'net_profit_yoy'">
                <span v-if="record.latest_report?.net_profit_yoy != null"
                  :class="getYoyClass(record.latest_report.net_profit_yoy)">
                  {{ record.latest_report.net_profit_yoy?.toFixed(2) }}%
                </span>
                <span v-else>-</span>
              </template>
            </template>
          </a-table>
          <a-empty v-if="!loading && watchlist.length === 0" description="暂无自选股">
            <template #description>
              <span>暂无自选股，点击右上角按钮添加股票</span>
            </template>
          </a-empty>
        </a-spin>
      </a-card>
    </div>

    <!-- 添加股票弹窗 -->
    <a-modal
      v-model:open="addModalVisible"
      title="添加自选股"
      @ok="confirmAdd"
      :confirm-loading="addLoading"
      okText="添加"
      cancelText="取消"
      :width="480"
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
      :width="400"
    >
      <a-input v-model:value="newGroupName" placeholder="请输入分组名称" size="large" />
    </a-modal>

    <!-- 重命名分组弹窗 -->
    <a-modal
      v-model:open="showRenameGroupModal"
      title="重命名分组"
      @ok="confirmRenameGroup"
      :confirm-loading="renameGroupLoading"
      okText="确定"
      cancelText="取消"
      :width="400"
    >
      <a-input v-model:value="renameGroupName" placeholder="请输入分组名称" size="large" />
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
import {
  PlusOutlined, CloudDownloadOutlined, ArrowLeftOutlined,
  AppstoreOutlined, FolderOutlined, LineChartOutlined,
  EditOutlined, DeleteOutlined
} from '@ant-design/icons-vue'
import { watchlistApi, stockApi, collectorApi, type WatchlistItem, type SearchResult } from '@/api/finance'

const router = useRouter()
const loading = ref(false)
const collecting = ref(false)
const watchlist = ref<WatchlistItem[]>([])
const allWatchlist = ref<WatchlistItem[]>([])
const collectingMap = ref<Record<string, boolean>>({})

// 视图模式
const viewMode = ref<'cards' | 'list'>('cards')
const currentGroupId = ref('all')

// 分组相关
interface Group { id: number; name: string; stock_count: number }
const groups = ref<Group[]>([])
const showAddGroupModal = ref(false)
const newGroupName = ref('')
const addGroupLoading = ref(false)

// 分组颜色映射
const GROUP_COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16']
function getGroupColor(groupId: number): string {
  if (groupId === 0) return '#8c8c8c'
  return GROUP_COLORS[(groupId - 1) % GROUP_COLORS.length]
}

// 添加股票表单
const addModalVisible = ref(false)
const addForm = ref({ code: '', name: '', groupId: 0 })
const addLoading = ref(false)

// 排序状态
const sorter = ref<{ field: string | null; order: string | null }>({ field: null, order: null })

// 重命名分组
const showRenameGroupModal = ref(false)
const renameGroupId = ref<number | null>(null)
const renameGroupName = ref('')
const renameGroupLoading = ref(false)

// 总股票数
const totalCount = computed(() => allWatchlist.value.length)

// 全部平均ROE
const allAvgRoe = computed(() => {
  const roes = allWatchlist.value
    .filter(w => w.latest_report?.roe != null)
    .map(w => w.latest_report!.roe!)
  if (roes.length === 0) return '0.00'
  return (roes.reduce((a, b) => a + b, 0) / roes.length).toFixed(2)
})

// 当前分组标题
const currentGroupTitle = computed(() => {
  if (currentGroupId.value === 'all') return '全部公司'
  const g = groups.value.find(x => String(x.id) === currentGroupId.value)
  return g?.name || '分组'
})

// 排序后的列表
const sortedWatchlist = computed(() => {
  const list = [...watchlist.value]
  if (!sorter.value.field || !sorter.value.order) return list

  const field = sorter.value.field
  const order = sorter.value.order

  const getVal = (item: WatchlistItem): any => {
    switch (field) {
      case 'stock_name': return item.stock_name || ''
      case 'latest_report': return item.latest_report?.report_date || ''
      case 'total_revenue': return item.latest_report?.total_revenue ?? -Infinity
      case 'net_profit_parent': return item.latest_report?.net_profit_parent ?? -Infinity
      case 'roe': return item.latest_report?.roe ?? -Infinity
      case 'debt_ratio': return item.latest_report?.debt_ratio ?? -Infinity
      case 'revenue_yoy': return item.latest_report?.revenue_yoy ?? -Infinity
      case 'net_profit_yoy': return item.latest_report?.net_profit_yoy ?? -Infinity
      default: return ''
    }
  }

  list.sort((a, b) => {
    const va = getVal(a)
    const vb = getVal(b)
    if (typeof va === 'number' && typeof vb === 'number') {
      return order === 'ascend' ? va - vb : vb - va
    }
    return order === 'ascend'
      ? String(va).localeCompare(String(vb))
      : String(vb).localeCompare(String(va))
  })
  return list
})

function handleTableChange(_pag: any, _filters: any, sorterInfo: any) {
  if (sorterInfo && sorterInfo.field) {
    sorter.value = { field: sorterInfo.key, order: sorterInfo.order }
  } else {
    sorter.value = { field: null, order: null }
  }
}

// 列表列定义
const columns = [
  { title: '分组', key: 'group_name', width: 120 },
  { title: '股票', key: 'stock_name', width: 130, fixed: 'left' as const, sorter: true },
  { title: '最新年报期', key: 'latest_report', width: 100, sorter: true },
  { title: '营业总收入', key: 'total_revenue', width: 110, align: 'right' as const, sorter: true },
  { title: '归母净利润', key: 'net_profit_parent', width: 110, align: 'right' as const, sorter: true },
  { title: 'ROE', key: 'roe', width: 70, align: 'right' as const, sorter: true },
  { title: '资产负债率', key: 'debt_ratio', width: 90, align: 'right' as const, sorter: true },
  { title: '营收同比', key: 'revenue_yoy', width: 80, align: 'right' as const, sorter: true },
  { title: '利润同比', key: 'net_profit_yoy', width: 80, align: 'right' as const, sorter: true },
  { title: '财报分析', key: 'fin_analysis', width: 90, align: 'center' as const },
  { title: '操作', key: 'action', width: 80, align: 'center' as const, fixed: 'right' as const },
]

// 获取分组已采集数量
function getGroupCollectedCount(groupId: number): number {
  return allWatchlist.value.filter(w => (w.group_id || 0) === groupId && w.latest_report).length
}

// 打开分组详情
function openGroupDetail(groupId: string) {
  currentGroupId.value = groupId
  viewMode.value = 'list'
  // 设置添加股票的默认分组
  if (groupId === 'all') {
    addForm.value.groupId = 0
  } else {
    addForm.value.groupId = parseInt(groupId)
  }
  loadWatchlist(groupId)
}

// 返回卡片视图
function backToCards() {
  viewMode.value = 'cards'
}

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

async function loadAllWatchlist() {
  try {
    const res = await watchlistApi.list()
    if (res.code === 0) {
      allWatchlist.value = res.data || []
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadWatchlist(groupId: string = currentGroupId.value) {
  loading.value = true
  try {
    const gid = groupId === 'all' ? undefined : parseInt(groupId)
    const res = await watchlistApi.list(gid)
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
    await loadAllWatchlist()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '创建失败')
  } finally {
    addGroupLoading.value = false
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
    loadAllWatchlist()
  } catch (e) {
    message.error('移除失败')
  }
}

async function moveStockGroup(record: WatchlistItem) {
  try {
    await watchlistApi.moveStock(record.stock_code, record.group_id || 0)
    message.success('分组已更新')
    record.group_name = record.group_id === 0
      ? '默认分组'
      : groups.value.find(g => g.id === record.group_id)?.name || '默认分组'
    loadGroups()
    loadAllWatchlist()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '移动失败')
    loadWatchlist()
  }
}

function showRenameGroup(g: Group) {
  renameGroupId.value = g.id
  renameGroupName.value = g.name
  showRenameGroupModal.value = true
}

async function confirmRenameGroup() {
  if (!renameGroupName.value.trim() || renameGroupId.value == null) {
    message.warning('请输入分组名称')
    return
  }
  renameGroupLoading.value = true
  try {
    await watchlistApi.renameGroup(renameGroupId.value, renameGroupName.value.trim())
    message.success('分组已更新')
    showRenameGroupModal.value = false
    renameGroupId.value = null
    renameGroupName.value = ''
    await loadGroups()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '重命名失败')
  } finally {
    renameGroupLoading.value = false
  }
}

async function deleteGroup(id: number) {
  try {
    await watchlistApi.deleteGroup(id)
    message.success('分组已删除')
    await loadGroups()
    await loadAllWatchlist()
    if (currentGroupId.value === String(id)) {
      viewMode.value = 'cards'
    }
  } catch (e: any) {
    message.error(e?.response?.data?.message || '删除失败')
  }
}

async function collectAll() {
  collecting.value = true
  try {
    await collectorApi.triggerCollect('watchlist')
    message.success('采集任务已启动，请稍候刷新查看')
    setTimeout(() => {
      loadWatchlist()
      loadAllWatchlist()
    }, 5000)
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
      loadAllWatchlist()
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
  const currentGroupId = groupId // 保存当前分组ID
  try {
    const res = await watchlistApi.add(code || name, undefined, groupId || 0)
    if (res.code === 0) {
      message.success('添加成功，可点击"采集"按钮获取财务数据')
      addModalVisible.value = false
      // 只清空代码和名称，保留分组
      addForm.value = { code: '', name: '', groupId: currentGroupId }
      loadWatchlist()
      loadGroups()
      loadAllWatchlist()
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
  loadAllWatchlist()
})
</script>

<style scoped>
.home-page { min-height: calc(100vh - 96px); }

.fade-in { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* 分组卡片视图 */
.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.view-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
}
.view-subtitle {
  font-size: 14px;
  color: #999;
  margin: 4px 0 0 0;
}
.header-actions { display: flex; gap: 12px; }

.group-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.group-card {
  position: relative;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 16px;
  padding: 24px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s ease;
}
.card-hover:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1);
  border-color: #1d4ed8;
}

.card-gradient {
  position: absolute;
  top: 0;
  right: 0;
  width: 120px;
  height: 120px;
  border-radius: 0 0 0 60px;
  opacity: 0.6;
  pointer-events: none;
}
.gradient-all {
  background: linear-gradient(135deg, #1d4ed822 0%, #1d4ed805 100%);
}

.card-content {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 16px;
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: #1d4ed8;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3);
}
.icon-all {
  background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%);
}

.card-info { flex: 1; min-width: 0; }
.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 2px 0;
}
.card-desc {
  font-size: 12px;
  color: #999;
  margin: 0 0 12px 0;
}
.card-stats {
  display: flex;
  gap: 20px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-label {
  font-size: 11px;
  color: #bbb;
}
.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

/* 新建分组卡片 */
.add-card {
  border-style: dashed;
  border-color: #d9d9d9;
  background: #fafafa;
}
.add-card:hover {
  border-color: #1d4ed8;
  background: #f0f7ff;
}
.add-card-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 100px;
  gap: 8px;
  color: #999;
}
.add-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
.add-card:hover .add-icon {
  background: #e6f0ff;
  color: #1d4ed8;
}
.add-text {
  font-size: 14px;
  font-weight: 500;
}

/* 分组卡片操作按钮 */
.card-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 2;
}
.group-card:hover .card-actions {
  opacity: 1;
}

/* 列表视图 */
.list-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.back-btn {
  flex-shrink: 0;
}
.list-title-area {
  flex: 1;
}
.list-title {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}
.list-subtitle {
  font-size: 13px;
  color: #999;
  margin: 2px 0 0 0;
}

.watchlist-card { border-radius: 12px; }

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
