<template>
  <div class="risk-center-page">
    <a-card title="风险排雷中心" class="risk-card">
      <template #extra>
        <a-space>
          <a-select
            v-model:value="filterGroup"
            placeholder="选择分组"
            style="width: 150px"
            allow-clear
            @change="loadRiskData"
          >
            <a-select-option v-for="group in groups" :key="group.group_name" :value="group.group_name">
              {{ group.group_name }}
            </a-select-option>
          </a-select>
          <a-select
            v-model:value="filterRiskLevel"
            placeholder="风险等级"
            style="width: 120px"
            allow-clear
            @change="loadRiskData"
          >
            <a-select-option value="low">低风险</a-select-option>
            <a-select-option value="medium">中风险</a-select-option>
            <a-select-option value="high">高风险</a-select-option>
            <a-select-option value="very_high">极高风险</a-select-option>
          </a-select>
          <a-button @click="loadRiskData">
            <ReloadOutlined /> 刷新
          </a-button>
        </a-space>
      </template>

      <a-spin :spinning="loading">
        <a-table
          :columns="columns"
          :data-source="riskData"
          :pagination="pagination"
          @change="handleTableChange"
          class="risk-table"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'stock_name'">
              <a @click="goToStock(record.stock_code)">
                {{ record.stock_name }}
                <a-tag v-if="record.is_st" color="red" size="small">ST</a-tag>
              </a>
            </template>
            <template v-else-if="column.key === 'risk_level'">
              <RiskBadge :level="record.risk_level" />
            </template>
            <template v-else-if="column.key === 'total_score'">
              <a-tag :color="getScoreColor(record.total_score)">
                {{ record.total_score }}分
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a @click="showRiskDetail(record)">查看详情</a>
            </template>
          </template>
        </a-table>
      </a-spin>
    </a-card>

    <a-modal
      v-model:open="detailModalVisible"
      title="风险详情"
      width="800px"
      :footer="null"
    >
      <a-descriptions bordered :column="2" v-if="selectedRisk">
        <a-descriptions-item label="股票名称">{{ selectedRisk.stock_name }}</a-descriptions-item>
        <a-descriptions-item label="股票代码">{{ selectedRisk.stock_code }}</a-descriptions-item>
        <a-descriptions-item label="报告日期">{{ selectedRisk.report_date }}</a-descriptions-item>
        <a-descriptions-item label="风险等级">
          <RiskBadge :level="selectedRisk.risk_level" />
        </a-descriptions-item>
        <a-descriptions-item label="总分" :span="2">
          <a-tag :color="getScoreColor(selectedRisk.total_score)">
            {{ selectedRisk.total_score }}分
          </a-tag>
        </a-descriptions-item>
      </a-descriptions>
      <a-divider>风险规则</a-divider>
      <a-list :data-source="selectedRisk?.rules || []">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-badge
              :status="item.passed ? 'success' : 'error'"
              :text="item.passed ? '通过' : '未通过'"
            />
            <template #actions>
              <span>{{ item.rule_name }}</span>
              <span>{{ item.detail }}</span>
              <span :class="item.passed ? 'positive' : 'negative'">
                {{ item.passed ? '+' : '' }}{{ item.score }}分
              </span>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ReloadOutlined } from '@ant-design/icons-vue'
import RiskBadge from '@/components/RiskBadge.vue'
import { getWatchlistGroups } from '@/api/watchlist'
import { getRiskAssessment } from '@/api/stock'
import type { WatchlistGroup, RiskAssessment } from '@/types'

const router = useRouter()

const loading = ref(false)
const groups = ref<WatchlistGroup[]>([])
const filterGroup = ref<string | undefined>()
const filterRiskLevel = ref<string | undefined>()
const riskData = ref<RiskAssessment[]>([])
const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const detailModalVisible = ref(false)
const selectedRisk = ref<RiskAssessment | null>(null)

const columns = [
  { title: '股票名称', key: 'stock_name' },
  { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code' },
  { title: '报告日期', dataIndex: 'report_date', key: 'report_date' },
  { title: '风险等级', key: 'risk_level' },
  { title: '总分', key: 'total_score' },
  { title: '操作', key: 'action' }
]

const loadGroups = async () => {
  try {
    const response = await getWatchlistGroups()
    if (response.data.code === 200) {
      groups.value = response.data.data || []
    }
  } catch (error) {
    console.error('Failed to load groups:', error)
  }
}

const loadRiskData = async () => {
  loading.value = true
  riskData.value = []

  try {
    const allStocks: { code: string; name: string; is_st: boolean }[] = []

    if (filterGroup.value) {
      const group = groups.value.find(g => g.group_name === filterGroup.value)
      if (group) {
        allStocks.push(...group.stocks.map(s => ({
          code: s.stock_code,
          name: s.stock_name,
          is_st: false
        })))
      }
    } else {
      groups.value.forEach(g => {
        allStocks.push(...g.stocks.map(s => ({
          code: s.stock_code,
          name: s.stock_name,
          is_st: false
        })))
      })
    }

    const riskResults = await Promise.all(
      allStocks.map(async (stock) => {
        try {
          const response = await getRiskAssessment(stock.code)
          if (response.data.code === 200) {
            return {
              ...response.data.data,
              stock_name: stock.name,
              is_st: stock.is_st
            }
          }
        } catch {
          return null
        }
        return null
      })
    )

    riskData.value = riskResults
      .filter(r => r !== null)
      .filter(r => !filterRiskLevel.value || r!.risk_level === filterRiskLevel.value) as RiskAssessment[]

    pagination.value.total = riskData.value.length
  } catch (error) {
    console.error('Failed to load risk data:', error)
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag: any) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
}

const getScoreColor = (score: number): string => {
  if (score >= 80) return 'green'
  if (score >= 60) return 'blue'
  if (score >= 40) return 'orange'
  return 'red'
}

const showRiskDetail = (record: RiskAssessment) => {
  selectedRisk.value = record
  detailModalVisible.value = true
}

const goToStock = (code: string) => {
  router.push(`/stock/${code}`)
}

onMounted(() => {
  loadGroups().then(() => loadRiskData())
})
</script>

<style scoped>
.risk-center-page {
  padding: 16px;
}

.risk-card {
  min-height: 500px;
}

.positive {
  color: #52c41a;
}

.negative {
  color: #ff4d4f;
}
</style>
