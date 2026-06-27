<template>
  <div class="announcement-page">
    <a-card title="新闻公告" class="announcement-card">
      <template #extra>
        <a-space wrap>
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索公告标题"
            style="width: 200px"
            @search="handleSearch"
            @pressEnter="handleSearch"
          />
          <a-input-search
            v-model:value="stockKeyword"
            placeholder="股票代码或名称"
            style="width: 150px"
            @search="handleSearch"
            @pressEnter="handleSearch"
          />
          <a-select
            v-model:value="filterType"
            placeholder="公告类型"
            style="width: 130px"
            allow-clear
            @change="handleSearch"
          >
            <a-select-option value="">全部类型</a-select-option>
            <a-select-option v-for="t in annTypes" :key="t" :value="t">
              {{ t }}
            </a-select-option>
          </a-select>
          <a-select
            v-model:value="days"
            placeholder="时间范围"
            style="width: 100px"
            @change="handleSearch"
          >
            <a-select-option :value="1">今日</a-select-option>
            <a-select-option :value="3">近3天</a-select-option>
            <a-select-option :value="7">近7天</a-select-option>
            <a-select-option :value="15">近15天</a-select-option>
          </a-select>
          <a-button @click="handleSearch">
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
              <a
                href="javascript:void(0)"
                class="announce-title-link"
                @click="openAnnouncement(record.url)"
              >
                {{ record.title }}
              </a>
            </template>
            <template v-else-if="column.key === 'stock_name'">
              <a @click="goToStock(record.stock_code)">
                {{ record.stock_name || record.stock_code }}
              </a>
            </template>
            <template v-else-if="column.key === 'ann_type'">
              <a-tag :color="getTypeColor(record.ann_type)">
                {{ record.ann_type }}
              </a-tag>
            </template>
          </template>
        </a-table>
        <a-empty v-if="!loading && announcements.length === 0 && !errorMsg" description="暂无公告数据" />
        <a-result v-if="errorMsg && !loading" status="warning" :title="errorMsg" sub-title="请稍后重试刷新">
          <template #extra>
            <a-button type="primary" @click="loadAnnouncements">重试</a-button>
          </template>
        </a-result>
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { get } from '@/api'

interface Announcement {
  stock_code: string
  stock_name: string
  title: string
  ann_type: string
  disclosure_date: string
  url: string
}

const router = useRouter()

const loading = ref(false)
const searchKeyword = ref('')
const stockKeyword = ref('')
const filterType = ref('')
const days = ref(7)
const announcements = ref<Announcement[]>([])
const annTypes = ref<string[]>([
  '定期报告', '业绩预告', '重大事项', '风险提示',
  '分配方案实施', '股份质押、冻结', '回购预案',
  '高管人员任职变动', '法律意见书', '监事会决议公告', '股东会决议公告',
])
const errorMsg = ref('')
const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const columns = [
  { title: '股票', key: 'stock_name', width: 120, fixed: 'left' as const },
  { title: '公告标题', key: 'title', ellipsis: true },
  { title: '公告类型', key: 'ann_type', width: 120 },
  { title: '披露日期', dataIndex: 'disclosure_date', key: 'disclosure_date', width: 120 },
]

function getTypeColor(type: string): string {
  if (type.includes('风险') || type.includes('退市') || type.includes('亏损')) return 'red'
  if (type.includes('业绩') || type.includes('利润')) return 'green'
  if (type.includes('定期') || type.includes('年报') || type.includes('季报')) return 'blue'
  if (type.includes('分配') || type.includes('分红')) return 'orange'
  if (type.includes('质押') || type.includes('冻结')) return 'purple'
  if (type.includes('回购')) return 'cyan'
  return 'default'
}

function openAnnouncement(url: string) {
  if (!url) return
  if (!url.startsWith('http')) url = 'https://' + url
  window.location.href = url
}

function goToStock(code: string) {
  if (code) {
    router.push(`/stock/${code}/main-indicators`)
  }
}

function handleSearch() {
  pagination.value.current = 1
  loadAnnouncements()
}

function handleTableChange(pag: any) {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  loadAnnouncements()
}

async function loadAnnouncements() {
  loading.value = true
  errorMsg.value = ''

  try {
    const params: any = {
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
      days: days.value,
    }

    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }
    if (stockKeyword.value) {
      params.stock = stockKeyword.value
    }
    if (filterType.value) {
      params.ann_type = filterType.value
    }

    const res: any = await get('/api/v1/announcements/', params)

    if (res.code === 0) {
      announcements.value = res.data?.items || []
      pagination.value.total = res.data?.total || 0
    } else {
      errorMsg.value = res.message || '加载失败'
    }
  } catch (error: any) {
    console.error('Failed to load announcements:', error)
    errorMsg.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
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

.announce-title-link {
  color: #1d4ed8;
  text-decoration: none;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.announce-title-link:hover {
  text-decoration: underline;
}
</style>
