<template>
  <div class="announcement-page">
    <a-card title="公告信息" class="ann-card">
      <!-- 筛选工具栏 -->
      <div class="filter-bar">
        <a-input-search
          v-model:value="keyword"
          placeholder="搜索公告标题..."
          style="width: 240px"
          @search="loadAnnouncements"
          allow-clear
        />
        <a-select
          v-model:value="filterStock"
          placeholder="股票"
          style="width: 140px"
          allow-clear
          show-search
          :filter-option="false"
          @search="searchStock"
          @change="loadAnnouncements"
        >
          <a-select-option v-for="s in stockOptions" :key="s.stock_code" :value="s.stock_code">
            {{ s.stock_name }} ({{ s.stock_code }})
          </a-select-option>
        </a-select>
        <a-select
          v-model:value="filterType"
          placeholder="公告类型"
          style="width: 160px"
          allow-clear
          @change="loadAnnouncements"
        >
          <a-select-option value="年度报告">年度报告</a-select-option>
          <a-select-option value="半年度报告">半年度报告</a-select-option>
          <a-select-option value="一季度报告">一季度报告</a-select-option>
          <a-select-option value="三季度报告">三季度报告</a-select-option>
          <a-select-option value="上市公告">上市公告</a-select-option>
          <a-select-option value="发行公告">发行公告</a-select-option>
          <a-select-option value="业绩预告">业绩预告</a-select-option>
          <a-select-option value="分红派息">分红派息</a-select-option>
          <a-select-option value="股东大会">股东大会</a-select-option>
          <a-select-option value="重大事项">重大事项</a-select-option>
          <a-select-option value="风险提示">风险提示</a-select-option>
          <a-select-option value="其他">其他</a-select-option>
        </a-select>
        <a-checkbox v-model:checked="filterRisk" @change="loadAnnouncements">仅看风险</a-checkbox>
        <a-button type="primary" @click="loadAnnouncements">查询</a-button>
        <a-button @click="resetFilter">重置</a-button>
      </div>

      <a-spin :spinning="loading">
        <a-table
          :columns="columns"
          :data-source="list"
          :pagination="pagination"
          @change="handleTableChange"
          size="small"
          row-key="id"
          class="ann-table"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'stock_code'">
              <a @click="$router.push(`/stock/${record.stock_code}`)">
                {{ record.stock_code }}
              </a>
            </template>
            <template v-else-if="column.key === 'ann_title'">
              <a @click="showDetail(record)">{{ record.ann_title }}</a>
              <a-badge v-if="record.is_risk" status="error" text="风险" style="margin-left: 8px" />
            </template>
            <template v-else-if="column.key === 'ann_type'">
              <a-tag :color="getTypeColor(record.ann_type)">{{ record.ann_type }}</a-tag>
            </template>
            <template v-else-if="column.key === 'publish_date'">
              {{ record.publish_date }}
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="showDetail(record)">查看</a-button>
            </template>
          </template>
        </a-table>
      </a-spin>
    </a-card>

    <!-- 详情弹窗 -->
    <a-modal
      v-model:open="detailVisible"
      :title="currentAnn?.ann_title"
      width="800px"
      :footer="null"
    >
      <div v-if="currentAnn">
        <a-descriptions size="small" :column="2" style="margin-bottom: 12px">
          <a-descriptions-item label="股票代码">
            <a @click="$router.push(`/stock/${currentAnn.stock_code}`)">{{ currentAnn.stock_code }}</a>
          </a-descriptions-item>
          <a-descriptions-item label="公告类型">
            <a-tag :color="getTypeColor(currentAnn.ann_type)">{{ currentAnn.ann_type }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="发布日期" :span="2">{{ currentAnn.publish_date }}</a-descriptions-item>
        </a-descriptions>
        <a-divider style="margin: 12px 0" />
        <div class="ann-detail-content">{{ currentAnn.content_summary || '暂无摘要内容' }}</div>
        <div v-if="currentAnn.pdf_url" style="margin-top: 12px">
          <a :href="currentAnn.pdf_url" target="_blank">查看原文PDF →</a>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getAnnouncements } from '@/api/announcement'
import { searchStocks } from '@/api/stock'
import type { TablePaginationConfig } from 'ant-design-vue'

const route = useRoute()

const loading = ref(false)
const list = ref<any[]>([])
const keyword = ref('')
const filterStock = ref<string | undefined>()
const filterType = ref<string | undefined>()
const filterRisk = ref(false)
const stockOptions = ref<any[]>([])
const detailVisible = ref(false)
const currentAnn = ref<any | null>(null)

const pagination = ref<TablePaginationConfig>({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const columns = [
  { title: '股票代码', key: 'stock_code', width: 120 },
  { title: '公告标题', key: 'ann_title', ellipsis: true },
  { title: '类型', key: 'ann_type', width: 120 },
  { title: '发布日期', key: 'publish_date', width: 120 },
  { title: '操作', key: 'action', width: 80 },
]

const getTypeColor = (type: string) => {
  if (!type) return 'default'
  if (type.includes('年报') || type.includes('年度报告')) return 'blue'
  if (type.includes('半年')) return 'cyan'
  if (type.includes('一季') || type.includes('Q1')) return 'green'
  if (type.includes('三季') || type.includes('Q3')) return 'lime'
  if (type.includes('发行') || type.includes('上市')) return 'purple'
  if (type.includes('业绩')) return 'magenta'
  if (type.includes('分红') || type.includes('派息')) return 'gold'
  if (type.includes('股东大会')) return 'volcano'
  if (type.includes('重大')) return 'red'
  if (type.includes('风险')) return 'red'
  if (type.includes('监管')) return 'orange'
  return 'default'
}

const loadAnnouncements = async () => {
  loading.value = true
  try {
    const res = await getAnnouncements({
      keyword: keyword.value || undefined,
      stock_code: filterStock.value,
      ann_type: filterType.value,
      is_risk: filterRisk.value ? true : undefined,
      page: pagination.value.current || 1,
      page_size: pagination.value.pageSize || 20,
    })
    if (res.data.code === 200) {
      list.value = res.data.data.items || []
      pagination.value.total = res.data.data.total || 0
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const searchStock = async (value: string) => {
  if (!value) {
    stockOptions.value = []
    return
  }
  try {
    const res = await searchStocks({ keyword: value, page: 1, page_size: 10 })
    if (res.data.code === 200) {
      stockOptions.value = res.data.data.items || []
    }
  } catch (e) {
    console.error(e)
  }
}

const handleTableChange = (pag: TablePaginationConfig) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  loadAnnouncements()
}

const showDetail = (record: any) => {
  currentAnn.value = record
  detailVisible.value = true
}

const resetFilter = () => {
  keyword.value = ''
  filterStock.value = undefined
  filterType.value = undefined
  filterRisk.value = false
  pagination.value.current = 1
  loadAnnouncements()
}

onMounted(() => {
  if (route.query.stock) {
    filterStock.value = route.query.stock as string
  }
  loadAnnouncements()
})
</script>

<style scoped>
.announcement-page {
  padding: 16px;
}

.ann-card {
  min-height: 500px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.ann-table {
  margin-top: 8px;
}

.ann-detail-content {
  line-height: 1.8;
  color: #333;
  white-space: pre-wrap;
  font-size: 14px;
}
</style>
