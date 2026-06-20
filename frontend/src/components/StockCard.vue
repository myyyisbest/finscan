<template>
  <a-card class="stock-card" hoverable @click="handleClick">
    <template #title>
      <div class="card-header">
        <div class="stock-info">
          <span class="stock-name">{{ stock.stock_name }}</span>
          <a-tag v-if="stock.is_st" color="red" size="small">ST</a-tag>
        </div>
        <span class="stock-code mono-number">{{ stock.stock_code }}</span>
      </div>
    </template>
    <div class="metrics-grid">
      <div class="metric-item">
        <span class="metric-label">营收</span>
        <span class="metric-value mono-number">{{ formatNumber(overview?.latest_annual?.revenue) }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">净利润</span>
        <span class="metric-value mono-number">{{ formatNumber(overview?.latest_annual?.net_profit) }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">ROE</span>
        <span class="metric-value mono-number" :class="getValueClass(overview?.latest_annual?.roe)">
          {{ formatPercent(overview?.latest_annual?.roe) }}
        </span>
      </div>
      <div class="metric-item">
        <span class="metric-label">ROA</span>
        <span class="metric-value mono-number" :class="getValueClass(overview?.latest_annual?.roa)">
          {{ formatPercent(overview?.latest_annual?.roa) }}
        </span>
      </div>
      <div class="metric-item">
        <span class="metric-label">资产负债率</span>
        <span class="metric-value mono-number">
          {{ formatPercent(overview?.latest_annual?.debt_to_assets) }}
        </span>
      </div>
      <div class="metric-item">
        <span class="metric-label">风险等级</span>
        <RiskBadge :level="riskLevel" />
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStockOverview } from '@/api/stock'
import type { StockOverview, StockSearchItem } from '@/types'
import RiskBadge from './RiskBadge.vue'

const props = defineProps<{
  stock: StockSearchItem
}>()

const router = useRouter()
const overview = ref<StockOverview | null>(null)
const riskLevel = ref<'low' | 'medium' | 'high' | 'very_high' | 'excluded'>('low')

onMounted(async () => {
  try {
    const response = await getStockOverview(props.stock.stock_code)
    if (response.data.code === 200) {
      overview.value = response.data.data
    }
  } catch (error) {
    console.error('Failed to load overview:', error)
  }
})

const handleClick = () => {
  router.push(`/stock/${props.stock.stock_code}`)
}

const formatNumber = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-'
  if (Math.abs(value) >= 1e8) {
    return (value / 1e8).toFixed(2) + ' 亿'
  }
  return value.toFixed(2)
}

const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2) + '%'
}

const getValueClass = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return ''
  return value >= 0 ? 'positive' : 'negative'
}
</script>

<style scoped>
.stock-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.stock-card:hover {
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stock-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-name {
  font-weight: 600;
  font-size: 16px;
}

.stock-code {
  color: #999;
  font-size: 14px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 12px;
  color: #999;
}

.metric-value {
  font-size: 14px;
  font-weight: 500;
}
</style>
