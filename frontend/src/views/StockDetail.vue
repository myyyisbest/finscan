<template>
  <div class="stock-detail-page">
    <a-spin :spinning="loading">
      <div class="stock-header">
        <div class="stock-title">
          <h1>{{ stockName }}</h1>
          <a-tag v-if="isST" color="red">ST</a-tag>
          <span class="stock-code mono-number">{{ stockCode }}</span>
        </div>
        <div class="stock-info">
          <span>{{ industry || '未知行业' }}</span>
          <span>{{ market || '未知市场' }}</span>
        </div>
      </div>

      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="overview" tab="财务总览">
          <div class="overview-section">
            <a-row :gutter="[16, 16]">
              <a-col :span="4">
                <a-card class="metric-card">
                  <a-statistic
                    title="ROE (净资产收益率)"
                    :value="overview?.latest_annual?.roe"
                    :precision="2"
                    suffix="%"
                    :value-style="{ color: getValueColor(overview?.latest_annual?.roe) }"
                  />
                </a-card>
              </a-col>
              <a-col :span="4">
                <a-card class="metric-card">
                  <a-statistic
                    title="ROA (资产收益率)"
                    :value="overview?.latest_annual?.roa"
                    :precision="2"
                    suffix="%"
                    :value-style="{ color: getValueColor(overview?.latest_annual?.roa) }"
                  />
                </a-card>
              </a-col>
              <a-col :span="4">
                <a-card class="metric-card">
                  <a-statistic
                    title="毛利率"
                    :value="overview?.latest_annual?.gross_margin"
                    :precision="2"
                    suffix="%"
                  />
                </a-card>
              </a-col>
              <a-col :span="4">
                <a-card class="metric-card">
                  <a-statistic
                    title="资产负债率"
                    :value="overview?.latest_annual?.debt_to_assets"
                    :precision="2"
                    suffix="%"
                  />
                </a-card>
              </a-col>
              <a-col :span="4">
                <a-card class="metric-card">
                  <a-statistic
                    title="营收"
                    :value="formatRevenue(overview?.latest_annual?.revenue)"
                    :value-style="{ fontSize: '18px' }"
                  />
                </a-card>
              </a-col>
              <a-col :span="4">
                <a-card class="metric-card">
                  <a-statistic
                    title="净利润"
                    :value="formatRevenue(overview?.latest_annual?.net_profit)"
                    :value-style="{ fontSize: '18px' }"
                  />
                </a-card>
              </a-col>
            </a-row>
            <a-card class="chart-card" title="指标趋势">
              <IndicatorChart :indicators="indicators" :stock-name="stockName" />
            </a-card>
          </div>
        </a-tab-pane>

        <a-tab-pane key="balance" tab="资产负债表">
          <FinTable type="balance" :stock-code="stockCode" />
        </a-tab-pane>

        <a-tab-pane key="income" tab="利润表">
          <FinTable type="income" :stock-code="stockCode" />
        </a-tab-pane>

        <a-tab-pane key="cashflow" tab="现金流量表">
          <FinTable type="cashflow" :stock-code="stockCode" />
        </a-tab-pane>

        <a-tab-pane key="indicators" tab="财务指标">
          <FinTable type="indicators" :stock-code="stockCode" />
        </a-tab-pane>

        <a-tab-pane key="risk" tab="风险评估">
          <div class="risk-section">
            <a-card class="risk-summary">
              <a-row>
                <a-col :span="12">
                  <a-statistic
                    title="风险等级"
                    :value="riskAssessment?.risk_level || '未知'"
                    :value-style="{ color: getRiskColor(riskAssessment?.risk_level) }"
                  />
                </a-col>
                <a-col :span="12">
                  <a-statistic
                    title="总分"
                    :value="riskAssessment?.total_score || 0"
                    suffix="分"
                  />
                </a-col>
              </a-row>
            </a-card>
            <a-card title="风险规则检测" class="risk-rules">
              <a-list
                :data-source="riskAssessment?.rules || []"
                :loading="riskLoading"
              >
                <template #renderItem="{ item }">
                  <a-list-item>
                    <a-list-item-meta>
                      <template #avatar>
                        <a-badge
                          :status="item.passed ? 'success' : 'error'"
                          :text="item.passed ? '通过' : '未通过'"
                        />
                      </template>
                      <template #title>
                        {{ item.rule_name }}
                      </template>
                      <template #description>
                        {{ item.detail }}
                      </template>
                    </a-list-item-meta>
                    <template #actions>
                      <span class="rule-score" :class="{ positive: item.passed, negative: !item.passed }">
                        {{ item.passed ? '+' : '' }}{{ item.score }}分
                      </span>
                    </template>
                  </a-list-item>
                </template>
              </a-list>
            </a-card>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import FinTable from '@/components/FinTable.vue'
import IndicatorChart from '@/components/IndicatorChart.vue'
import { getStockOverview, getIndicators, getRiskAssessment } from '@/api/stock'
import type { StockOverview, FinIndicator, RiskAssessment } from '@/types'

const route = useRoute()
const stockCode = computed(() => route.params.code as string)

const loading = ref(false)
const riskLoading = ref(false)
const activeTab = ref('overview')
const stockName = ref('')
const isST = ref(false)
const industry = ref<string | null>(null)
const market = ref<string | null>(null)
const overview = ref<StockOverview | null>(null)
const indicators = ref<FinIndicator[]>([])
const riskAssessment = ref<RiskAssessment | null>(null)

const loadOverview = async () => {
  loading.value = true
  try {
    const response = await getStockOverview(stockCode.value)
    if (response.data.code === 200) {
      overview.value = response.data.data
      stockName.value = response.data.data.basic.stock_name
      isST.value = response.data.data.basic.is_st
      industry.value = response.data.data.basic.industry
      market.value = response.data.data.basic.market
    }
  } catch (error) {
    console.error('Failed to load overview:', error)
  } finally {
    loading.value = false
  }
}

const loadIndicators = async () => {
  try {
    const response = await getIndicators(stockCode.value, { page: 1, page_size: 100 })
    if (response.data.code === 200) {
      indicators.value = response.data.data.items || []
    }
  } catch (error) {
    console.error('Failed to load indicators:', error)
  }
}

const loadRiskAssessment = async () => {
  riskLoading.value = true
  try {
    const response = await getRiskAssessment(stockCode.value)
    if (response.data.code === 200) {
      riskAssessment.value = response.data.data
    }
  } catch (error) {
    console.error('Failed to load risk assessment:', error)
  } finally {
    riskLoading.value = false
  }
}

const formatRevenue = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-'
  if (Math.abs(value) >= 1e8) {
    return (value / 1e8).toFixed(2) + ' 亿'
  }
  return value.toFixed(2)
}

const getValueColor = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '#333'
  return value >= 0 ? '#52c41a' : '#ff4d4f'
}

const getRiskColor = (level: string | undefined): string => {
  if (!level) return '#999'
  switch (level) {
    case 'low': return '#52c41a'
    case 'medium': return '#faad14'
    case 'high': return '#ff7a45'
    case 'very_high': return '#ff4d4f'
    case 'excluded': return '#8c8c8c'
    default: return '#999'
  }
}

onMounted(() => {
  loadOverview()
  loadIndicators()
  loadRiskAssessment()
})
</script>

<style scoped>
.stock-detail-page {
  padding: 16px;
}

.stock-header {
  margin-bottom: 24px;
}

.stock-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stock-title h1 {
  margin: 0;
  font-size: 24px;
}

.stock-code {
  color: #999;
  font-size: 16px;
}

.stock-info {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  color: #666;
}

.overview-section {
  padding: 0;
}

.metric-card {
  text-align: center;
}

.chart-card {
  margin-top: 16px;
}

.risk-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.risk-summary {
  background: #fafafa;
}

.risk-rules {
  margin-top: 16px;
}

.rule-score {
  font-weight: 600;
}

.rule-score.positive {
  color: #52c41a;
}

.rule-score.negative {
  color: #ff4d4f;
}
</style>
