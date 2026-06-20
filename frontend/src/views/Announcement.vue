<template>
  <div class="announcement-page">
    <a-card title="公告中心" class="announcement-card">
      <template #extra>
        <a-space>
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索公告标题"
            style="width: 200px"
            @search="loadAnnouncements"
          />
          <a-select
            v-model:value="filterType"
            placeholder="公告类型"
            style="width: 120px"
            allow-clear
            @change="loadAnnouncements"
          >
            <a-select-option value="定期报告">定期报告</a-select-option>
            <a-select-option value="业绩预告">业绩预告</a-select-option>
            <a-select-option value="重大事项">重大事项</a-select-option>
            <a-select-option value="风险提示">风险提示</a-select-option>
            <a-select-option value="其他">其他</a-select-option>
          </a-select>
          <a-select
            v-model:value="filterRisk"
            placeholder="风险相关"
            style="width: 120px"
            allow-clear
            @change="loadAnnouncements"
          >
            <a-select-option :value="true">仅风险公告</a-select-option>
            <a-select-option :value="false">全部</a-select-option>
          </a-select>
          <a-button @click="loadAnnouncements">
            <ReloadOutlined /> 刷新
          </a-button>
        </a-space>
      </template>

      <a-spin :spinning="loading">
        <a-table
          :columns="columns"
          :data-source="announcements"
          :pagination="pagination"
          @change="handleTableChange"
          class="announcement-table"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'title'">
              <a @click="showDetail(record)">{{ record.title }}</a>
            </template>
            <template v-else-if="column.key === 'ann_type'">
              <a-tag :color="getTypeColor(record.ann_type)">
                {{ record.ann_type }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'is_risk'">
              <a-badge
                :status="record.is_risk ? 'error' : 'default'"
                :text="record.is_risk ? '风险' : '正常'"
              />
            </template>
            <template v-else-if="column.key === 'stock_name'">
              <a v-if="record.stock_code" @click="goToStock(record.stock_code)">
                {{ record.stock_name || record.stock_code }}
              </a>
              <span v-else>-</span>
            </template>
          </template>
        </a-table>
      </a-spin>
    </a-card>

    <a-modal
      v-model:open="detailModalVisible"
      :title="selectedAnnouncement?.title"
      width="800px"
      :footer="null"
    >
      <a-descriptions bordered :column="2" v-if="selectedAnnouncement">
        <a-descriptions-item label="股票名称">
          <a @click="goToStock(selectedAnnouncement.stock_code)">
            {{ selectedAnnouncement.stock_name || '-' }}
          </a>
        </a-descriptions-item>
        <a-descriptions-item label="股票代码">{{ selectedAnnouncement.stock_code || '-' }}</a-descriptions-item>
        <a-descriptions-item label="公告类型">
          <a-tag :color="getTypeColor(selectedAnnouncement.ann_type)">
            {{ selectedAnnouncement.ann_type }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="披露日期">{{ selectedAnnouncement.disclosure_date }}</a-descriptions-item>
        <a-descriptions-item label="风险标识">
          <a-badge
            :status="selectedAnnouncement.is_risk ? 'error' : 'success'"
            :text="selectedAnnouncement.is_risk ? '风险相关' : '正常'"
          />
        </a-descriptions-item>
      </a-descriptions>
      <a-divider>公告内容</a-divider>
      <div class="announcement-content" v-if="selectedAnnouncement?.content">
        {{ selectedAnnouncement.content }}
      </div>
      <a-empty v-else description="暂无详细内容" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { get } from '@/api'
import type { Announcement } from '@/types'

const router = useRouter()

const loading = ref(false)
const searchKeyword = ref('')
const filterType = ref<string | undefined>()
const filterRisk = ref<boolean | undefined>()
const announcements = ref<Announcement[]>([])
const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const detailModalVisible = ref(false)
const selectedAnnouncement = ref<Announcement | null>(null)

const columns = [
  { title: '公告标题', key: 'title', ellipsis: true },
  { title: '股票', key: 'stock_name' },
  { title: '公告类型', key: 'ann_type' },
  { title: '披露日期', dataIndex: 'disclosure_date', key: 'disclosure_date' },
  { title: '风险标识', key: 'is_risk' }
]

const loadAnnouncements = async () => {
  loading.value = true

  try {
    const params: any = {
      page: pagination.value.current,
      page_size: pagination.value.pageSize
    }

    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }
    if (filterType.value) {
      params.ann_type = filterType.value
    }
    if (filterRisk.value !== undefined) {
      params.is_risk = filterRisk.value
    }

    const response = await get<any>('/api/v1/announcements', params)

    if (response.data.code === 200) {
      announcements.value = response.data.data.items || []
      pagination.value.total = response.data.data.total || 0
    }
  } catch (error) {
    console.error('Failed to load announcements:', error)
    message.error('加载公告失败')
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag: any) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  loadAnnouncements()
}

const getTypeColor = (type: string): string => {
  switch (type) {
    case '定期报告': return 'blue'
    case '业绩预告': return 'green'
    case '重大事项': return 'orange'
    case '风险提示': return 'red'
    default: return 'default'
  }
}

const showDetail = (record: Announcement) => {
  selectedAnnouncement.value = record
  detailModalVisible.value = true
}

const goToStock = (code: string | null) => {
  if (code) {
    router.push(`/stock/${code}`)
  }
}

onMounted(() => {
  loadAnnouncements()
})
</script>

<style scoped>
.announcement-page {
  padding: 16px;
}

.announcement-card {
  min-height: 500px;
}

.announcement-content {
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  line-height: 1.8;
}
</style>
