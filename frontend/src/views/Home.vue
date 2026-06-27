<template>
  <div class="home-page">
    <div class="page-header">
      <h2 class="page-title">我的自选</h2>
      <div class="header-actions">
        <a-button type="primary" @click="refreshData" :loading="loading">
          <ReloadOutlined /> 刷新数据
        </a-button>
        <a-button @click="collectAll" :loading="collecting">
          <CloudDownloadOutlined /> 采集数据
        </a-button>
      </div>
    </div>

    <a-card class="watchlist-card">
      <a-spin :spinning="loading">
        <a-table
          :columns="columns"
          :data-source="watchlist"
          :pagination="false"
          row-key="stock_code"
          :scroll="{ x: 1000 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'stock_name'">
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
        <a-empty v-if="!loading && watchlist.length === 0" description="暂无自选股，请通过上方搜索添加">
          <template #description>
            <span>暂无自选股，请使用顶部搜索框搜索并添加股票</span>
          </template>
        </a-empty>
      </a-spin>
    </a-card>

    <!-- 快速添加弹窗 -->
    <a-modal
      v-model:open="addModalVisible"
      title="添加自选股"
      @ok="confirmAdd"
      :confirm-loading="addLoading"
      okText="添加"
      cancelText="取消"
    >
      <a-input-search
        v-model:value="addKeyword"
        placeholder="输入股票代码（如002130）或名称搜索"
        size="large"
        @search="searchToAdd"
        @change="onKeywordChange"
        style="margin-bottom: 12px"
      />
      <div v-if="addSearchResults.length > 0" class="add-results">
        <div
          v-for="item in addSearchResults"
          :key="item.stock_code"
          class="add-result-item"
          :class="{ selected: selectedToAdd?.stock_code === item.stock_code }"
          @click="selectStock(item)"
        >
          <span class="code">{{ item.stock_code }}</span>
          <span class="name">{{ item.stock_name }}</span>
          <span v-if="item.industry" class="industry">{{ item.industry }}</span>
        </div>
      </div>
      <div v-else-if="isCodeInput" class="code-direct-add">
        <div class="direct-add-tip">
          <span class="code-badge">{{ addKeyword }}</span>
          <span class="tip-text">未搜索到该股票，可直接通过代码添加</span>
        </div>
      </div>
      <a-empty v-else-if="addKeyword && !addSearching" description="未找到股票，可输入6位股票代码直接添加" />
      <div class="add-tip">
        <a-tag color="blue">提示</a-tag>
        支持直接输入6位股票代码添加，添加后点击"采集"按钮获取财务数据
      </div>
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
import { PlusOutlined, ReloadOutlined, CloudDownloadOutlined } from '@ant-design/icons-vue'
import { watchlistApi, stockApi, collectorApi, type WatchlistItem, type SearchResult } from '@/api/finance'

const router = useRouter()
const loading = ref(false)
const collecting = ref(false)
const watchlist = ref<WatchlistItem[]>([])
const collectingMap = ref<Record<string, boolean>>({})

const addModalVisible = ref(false)
const addKeyword = ref('')
const addSearching = ref(false)
const addSearchResults = ref<SearchResult[]>([])
const selectedToAdd = ref<SearchResult | null>(null)
const addLoading = ref(false)

const isCodeInput = computed(() => {
  return /^\d{6}$/.test(addKeyword.value) && addSearchResults.value.length === 0 && !addSearching.value
})

const columns = [
  { title: '股票', key: 'stock_name', width: 180, fixed: 'left' as const },
  { title: '最新报告期', key: 'latest_report', width: 120 },
  { title: '营业总收入(万)', key: 'total_revenue', width: 150, align: 'right' as const },
  { title: '归母净利润(万)', key: 'net_profit_parent', width: 150, align: 'right' as const },
  { title: 'ROE(%)', key: 'roe', width: 100, align: 'right' as const },
  { title: '资产负债率(%)', key: 'debt_ratio', width: 120, align: 'right' as const },
  { title: '营收同比(%)', key: 'revenue_yoy', width: 120, align: 'right' as const },
  { title: '操作', key: 'action', width: 80, align: 'center' as const, fixed: 'right' as const },
]

async function loadWatchlist() {
  loading.value = true
  try {
    const res = await watchlistApi.list()
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

function formatWan(val: number) {
  if (val == null) return '-'
  const absVal = Math.abs(val)
  if (absVal >= 1e8) {
    return (val / 1e8).toFixed(2) + '亿'
  } else if (absVal >= 1e4) {
    return (val / 1e4).toFixed(2) + '万'
  }
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
    message.success('采集任务已启动，数据正在后台采集，请稍候刷新查看')
    // 5秒后自动刷新
    setTimeout(() => {
      loadWatchlist()
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
    // 8秒后自动刷新
    setTimeout(() => {
      loadWatchlist()
      collectingMap.value[record.stock_code] = false
    }, 8000)
  } catch (e) {
    message.error('启动采集失败')
    collectingMap.value[record.stock_code] = false
  }
}

let addSearchTimer: number | null = null

function onKeywordChange() {
  selectedToAdd.value = null
  if (addSearchTimer) clearTimeout(addSearchTimer)
  addSearchTimer = window.setTimeout(() => {
    searchToAdd()
  }, 300)
}

async function searchToAdd() {
  if (!addKeyword.value) {
    addSearchResults.value = []
    return
  }
  addSearching.value = true
  try {
    const res = await stockApi.search(addKeyword.value)
    if (res.code === 0) {
      addSearchResults.value = res.data || []
    }
  } finally {
    addSearching.value = false
  }
}

function selectStock(item: SearchResult) {
  selectedToAdd.value = item
}

async function confirmAdd() {
  let input = addKeyword.value.trim()
  if (!input) {
    message.warning('请输入股票代码或名称')
    return
  }

  let code = ''
  let name = ''

  if (selectedToAdd.value) {
    code = selectedToAdd.value.stock_code
    name = selectedToAdd.value.stock_name
  } else if (/^\d{6}$/.test(input)) {
    code = input
    name = input
  } else {
    // 输入的是名称，从搜索结果里找第一个匹配的
    const matched = addSearchResults.value.find(s => 
      s.stock_name === input || s.stock_name.includes(input)
    )
    if (matched) {
      code = matched.stock_code
      name = matched.stock_name
    } else {
      // 搜索结果为空但用户点了添加，直接把输入当关键词发后端验证
      code = input
      name = input
    }
  }

  addLoading.value = true
  try {
    await watchlistApi.add(code, name)
    message.success('添加成功，可点击"采集"按钮获取财务数据')
    addModalVisible.value = false
    addKeyword.value = ''
    selectedToAdd.value = null
    addSearchResults.value = []
    loadWatchlist()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '添加失败')
  } finally {
    addLoading.value = false
  }
}

onMounted(() => {
  loadWatchlist()
})
</script>

<style scoped>
.home-page {
  min-height: calc(100vh - 96px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.watchlist-card {
  background: #fff;
  border-radius: 8px;
}

.stock-link {
  display: flex;
  flex-direction: column;
  gap: 2px;
  cursor: pointer;
}

.stock-link:hover .stock-name-text {
  color: #1d4ed8;
}

.stock-code {
  font-size: 12px;
  color: #999;
}

.stock-name-text {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
}

.no-data {
  color: #ccc;
}

.profit-pos {
  color: #cf1322;
}

.profit-neg {
  color: #389e0d;
}

.roe-good {
  color: #cf1322;
  font-weight: 600;
}

.roe-ok {
  color: #d48806;
}

.roe-bad {
  color: #389e0d;
}

.fab-btn {
  position: fixed;
  bottom: 40px;
  right: 40px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #1d4ed8;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.4);
  transition: transform 0.2s;
  z-index: 50;
}

.fab-btn:hover {
  transform: scale(1.1);
  background: #1e40af;
}

.add-results {
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.add-result-item {
  padding: 10px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #f5f5f5;
}

.add-result-item:hover,
.add-result-item.selected {
  background: #e6f4ff;
}

.add-result-item .code {
  color: #1d4ed8;
  font-weight: 600;
  min-width: 70px;
}

.add-result-item .industry {
  font-size: 12px;
  color: #999;
  margin-left: auto;
}

.action-btns {
  display: flex;
  gap: 4px;
  align-items: center;
  justify-content: center;
}

.code-direct-add {
  padding: 20px;
  text-align: center;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  background: #fafafa;
}

.direct-add-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.code-badge {
  display: inline-block;
  padding: 4px 12px;
  background: #1d4ed8;
  color: #fff;
  border-radius: 4px;
  font-weight: 600;
  font-family: monospace;
}

.tip-text {
  color: #666;
  font-size: 14px;
}

.add-tip {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f0f7ff;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}
</style>
