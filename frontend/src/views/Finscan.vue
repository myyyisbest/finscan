<template>
  <div class="finscan-page">
    <div class="page-header">
      <div class="header-left">
        <h3 class="page-title">财报排雷</h3>
        <span class="page-subtitle">基于30条排雷规则的智能分析</span>
      </div>
      <div class="header-actions">
        <a-select
          v-model:value="selectedCode"
          show-search
          placeholder="选择自选股票或搜索"
          style="width: 240px"
          :filter-option="false"
          @search="onSearch"
          @change="onStockSelect"
          @focus="loadWatchlistStocks"
          size="large"
        >
          <a-select-option v-for="s in allOptions" :key="s.code" :value="s.code">
            {{ s.name }} ({{ s.code }})
          </a-select-option>
        </a-select>
        <a-button type="primary" size="large" :loading="analyzing" @click="analyze">
          <template #icon><SearchOutlined /></template>
          开始排雷
        </a-button>
      </div>
    </div>

    <div v-if="analyzing" class="loading-state">
      <div class="loading-content">
        <div class="loading-animation">
          <div class="loading-circles">
            <div class="circle c1"></div>
            <div class="circle c2"></div>
            <div class="circle c3"></div>
          </div>
          <div class="loading-icon">🔍</div>
        </div>
        <div class="loading-title">正在分析财报数据</div>
        <div class="loading-desc">请稍候，正在执行30条排雷规则检测…</div>
        <div class="loading-progress">
          <div class="progress-bar">
            <div class="progress-fill"></div>
          </div>
          <div class="loading-steps">
            <span :class="{ active: loadStep >= 1 }">数据获取</span>
            <span :class="{ active: loadStep >= 2 }">规则计算</span>
            <span :class="{ active: loadStep >= 3 }">结果汇总</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="report" class="report-content">
      <div class="stock-header">
        <div class="stock-info">
          <div class="stock-name-row">
            <span class="stock-name">{{ report.stock_name }}</span>
            <span class="stock-code">{{ report.stock_code }}</span>
          </div>
          <div class="stock-meta">
            <span class="meta-item">
              <CalendarOutlined />
              {{ report.report_year }}年年报
            </span>
            <span class="meta-item">
              <PieChartOutlined />
              共30条检测规则
            </span>
          </div>
        </div>
      </div>

      <div class="risk-dashboard">
        <div class="risk-gauge-card" :class="riskLevelClass">
          <div class="gauge-glow"></div>
          <div class="gauge-content">
            <div class="gauge-ring">
              <svg viewBox="0 0 120 120" class="gauge-svg">
                <circle cx="60" cy="60" r="52" class="gauge-bg" />
                <circle
                  cx="60" cy="60" r="52"
                  class="gauge-progress"
                  :stroke-dasharray="gaugeDashArray"
                  :stroke-dashoffset="gaugeDashOffset"
                />
              </svg>
              <div class="gauge-center">
                <div class="gauge-score">{{ report.total_score }}</div>
                <div class="gauge-unit">分</div>
              </div>
            </div>
            <div class="gauge-info">
              <div class="gauge-level">
                <span class="level-dot"></span>
                {{ riskLevelText }}
              </div>
              <div class="gauge-range">分数范围：{{ scoreRangeText }}</div>
            </div>
          </div>
          <div class="gauge-scale">
            <span>0</span>
            <span>25</span>
            <span>50</span>
            <span>75</span>
            <span>100+</span>
          </div>
        </div>

        <div class="stats-grid">
          <div
            class="stat-card stat-pass"
            :class="{ active: activeFilter === 'PASS' }"
            @click="toggleFilter('PASS')"
          >
            <div class="stat-icon">✓</div>
            <div class="stat-content">
              <div class="stat-number">{{ report.n_pass }}</div>
              <div class="stat-label">通过</div>
            </div>
            <div class="stat-hint">{{ activeFilter === 'PASS' ? '点击取消' : '点击筛选' }}</div>
          </div>
          <div
            class="stat-card stat-warn"
            :class="{ active: activeFilter === 'WARN' }"
            @click="toggleFilter('WARN')"
          >
            <div class="stat-icon">⚠</div>
            <div class="stat-content">
              <div class="stat-number">{{ report.n_warn }}</div>
              <div class="stat-label">警告</div>
            </div>
            <div class="stat-hint">{{ activeFilter === 'WARN' ? '点击取消' : '点击筛选' }}</div>
          </div>
          <div
            class="stat-card stat-fail"
            :class="{ active: activeFilter === 'FAIL' }"
            @click="toggleFilter('FAIL')"
          >
            <div class="stat-icon">✗</div>
            <div class="stat-content">
              <div class="stat-number">{{ report.n_fail }}</div>
              <div class="stat-label">失败</div>
            </div>
            <div class="stat-hint">{{ activeFilter === 'FAIL' ? '点击取消' : '点击筛选' }}</div>
          </div>
          <div
            class="stat-card stat-skip"
            :class="{ active: activeFilter === 'SKIP' }"
            @click="toggleFilter('SKIP')"
          >
            <div class="stat-icon">○</div>
            <div class="stat-content">
              <div class="stat-number">{{ report.n_skip }}</div>
              <div class="stat-label">跳过</div>
            </div>
            <div class="stat-hint">{{ activeFilter === 'SKIP' ? '点击取消' : '点击筛选' }}</div>
          </div>
        </div>
      </div>

      <div class="result-section">
        <div class="section-tabs">
          <div
            class="tab-item"
            :class="{ active: activeTab === 'layers' }"
            @click="activeTab = 'layers'"
          >
            <AppstoreOutlined />
            按层级查看
          </div>
          <div
            class="tab-item"
            :class="{ active: activeTab === 'all' }"
            @click="activeTab = 'all'"
          >
            <UnorderedListOutlined />
            全部规则
          </div>
          <div
            v-if="activeFilter"
            class="tab-item tab-filter active"
          >
            <FilterOutlined />
            筛选：{{ filterLabel }}({{ filteredResults.length }})
            <span class="close-filter" @click="activeFilter = ''">✕</span>
          </div>
        </div>

        <div class="section-content">
          <template v-if="activeFilter">
            <div class="rule-list">
              <RuleCard v-for="rule in filteredResults" :key="rule.code" :rule="rule" />
            </div>
            <a-empty v-if="filteredResults.length === 0" description="暂无该类型的检查项" />
          </template>

          <template v-else-if="activeTab === 'all'">
            <div class="rule-list">
              <RuleCard v-for="rule in sortedRules" :key="rule.code" :rule="rule" />
            </div>
          </template>

          <template v-else>
            <div class="layers-grid">
              <div
                v-for="layer in layerGroups"
                :key="layer.id"
                class="layer-card"
                :class="`layer-${layer.status}`"
              >
                <div class="layer-header">
                  <div class="layer-title">
                    <span class="layer-icon">{{ layer.icon }}</span>
                    {{ layer.name }}
                  </div>
                  <a-tag :color="layer.statusColor" size="small">
                    {{ layer.pass }}通过 / {{ layer.warn }}警告 / {{ layer.fail }}失败
                  </a-tag>
                </div>
                <div class="layer-rules">
                  <RuleCard
                    v-for="rule in layer.rules"
                    :key="rule.code"
                    :rule="rule"
                    compact
                  />
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div class="legend-section">
        <div class="legend-title">风险等级说明</div>
        <div class="legend-items">
          <div class="legend-item legend-low">
            <div class="legend-bar"></div>
            <div class="legend-text">
              <span class="legend-label">低风险</span>
              <span class="legend-range">0-10分</span>
            </div>
          </div>
          <div class="legend-item legend-medium">
            <div class="legend-bar"></div>
            <div class="legend-text">
              <span class="legend-label">中风险</span>
              <span class="legend-range">11-25分</span>
            </div>
          </div>
          <div class="legend-item legend-high">
            <div class="legend-bar"></div>
            <div class="legend-text">
              <span class="legend-label">高风险</span>
              <span class="legend-range">26-45分</span>
            </div>
          </div>
          <div class="legend-item legend-very-high">
            <div class="legend-bar"></div>
            <div class="legend-text">
              <span class="legend-label">极高风险</span>
              <span class="legend-range">46分以上</span>
            </div>
          </div>
          <div class="legend-item legend-reject">
            <div class="legend-bar"></div>
            <div class="legend-text">
              <span class="legend-label">一票否决</span>
              <span class="legend-range">999分</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!selectedCode" class="empty-state">
      <div class="empty-illustration">📊</div>
      <div class="empty-title">选择一只股票，开始排雷分析</div>
      <div class="empty-desc">
        基于《手把手教你读财报》30条排雷规则<br />
        从利润、现金流、资产负债等6个维度全面检测
      </div>
      <div class="empty-features">
        <div class="feature-item">
          <span class="feature-icon">🔒</span>
          <span>审计意见核查</span>
        </div>
        <div class="feature-item">
          <span class="feature-icon">💰</span>
          <span>利润质量分析</span>
        </div>
        <div class="feature-item">
          <span class="feature-icon">💸</span>
          <span>现金流健康度</span>
        </div>
        <div class="feature-item">
          <span class="feature-icon">📦</span>
          <span>资产风险检测</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { message } from 'ant-design-vue'
import {
  AppstoreOutlined, UnorderedListOutlined, FilterOutlined,
  CalendarOutlined, PieChartOutlined, SearchOutlined,
} from '@ant-design/icons-vue'
import { watchlistApi } from '@/api/finance'

interface SearchResult {
  code: string
  name: string
}

interface RuleResult {
  code: string
  name: string
  layer: number
  verdict: string
  score_added: number
  detail: string
  raw_values: any
}

interface Report {
  stock_code: string
  stock_name: string
  report_year: number
  total_score: number
  risk_level: string
  n_pass: number
  n_warn: number
  n_fail: number
  n_skip: number
  combo_bonus: number
  rule_results: RuleResult[]
}

const RuleCard = {
  props: {
    rule: { type: Object, required: true },
    compact: { type: Boolean, default: false },
  },
  setup(props: { rule: RuleResult; compact: boolean }) {
    const verdictMap: Record<string, { label: string; icon: string }> = {
      PASS: { label: '通过', icon: '✓' },
      WARN: { label: '警告', icon: '⚠' },
      FAIL: { label: '失败', icon: '✗' },
      SKIP: { label: '跳过', icon: '○' },
    }
    const v = computed(() => verdictMap[props.rule.verdict] || { label: props.rule.verdict, icon: '?' })
    return () => h('div', {
      class: ['rule-card', `rule-${props.rule.verdict.toLowerCase()}`, { compact: props.compact }],
    }, [
      h('div', { class: 'rule-card-bar' }),
      h('div', { class: 'rule-card-body' }, [
        h('div', { class: 'rule-card-head' }, [
          h('span', { class: 'rule-code' }, props.rule.code),
          h('span', { class: 'rule-name' }, props.rule.name),
          props.rule.score_added > 0
            ? h('span', { class: 'rule-score' }, `+${props.rule.score_added}分`)
            : null,
          h('span', { class: ['rule-verdict-badge', `badge-${props.rule.verdict.toLowerCase()}`] }, [
            h('span', { class: 'badge-icon' }, v.value.icon),
            v.value.label,
          ]),
        ]),
        h('div', { class: 'rule-card-detail' }, props.rule.detail),
      ]),
    ])
  }
}

const { h } = require('vue')

const selectedCode = ref<string>('')
const searchResults = ref<SearchResult[]>([])
const watchlistStocks = ref<SearchResult[]>([])
const analyzing = ref(false)
const report = ref<Report | null>(null)
const activeFilter = ref<string>('')
const activeTab = ref<string>('layers')
const loadStep = ref(0)
let loadTimer: any = null

const allOptions = computed(() => {
  if (searchResults.value.length > 0) return searchResults.value
  return watchlistStocks.value
})

const riskLevelClass = computed(() => {
  if (!report.value) return ''
  const level = report.value.risk_level
  if (level === 'REJECT') return 'risk-reject'
  if (level === 'VERY_HIGH') return 'risk-very-high'
  if (level === 'HIGH') return 'risk-high'
  if (level === 'MEDIUM') return 'risk-medium'
  return 'risk-low'
})

const riskLevelText = computed(() => {
  if (!report.value) return ''
  const map: Record<string, string> = {
    'LOW': '低风险',
    'MEDIUM': '中风险',
    'HIGH': '高风险',
    'VERY_HIGH': '极高风险',
    'REJECT': '一票否决',
  }
  return map[report.value.risk_level] || report.value.risk_level
})

const scoreRangeText = computed(() => {
  if (!report.value) return ''
  const map: Record<string, string> = {
    'LOW': '0-10分',
    'MEDIUM': '11-25分',
    'HIGH': '26-45分',
    'VERY_HIGH': '46分以上',
    'REJECT': '999分',
  }
  return map[report.value.risk_level] || ''
})

const gaugeDashArray = (52 * 2 * Math.PI).toFixed(2)

const gaugeDashOffset = computed(() => {
  if (!report.value) return gaugeDashArray
  const score = Math.min(report.value.total_score, 100)
  const percent = score / 100
  return (parseFloat(gaugeDashArray) * (1 - percent * 0.75)).toFixed(2)
})

const filterLabel = computed(() => {
  const map: Record<string, string> = {
    'PASS': '通过',
    'WARN': '警告',
    'FAIL': '失败',
    'SKIP': '跳过',
  }
  return map[activeFilter.value] || ''
})

const filteredResults = computed(() => {
  if (!activeFilter.value || !report.value) return []
  return report.value.rule_results.filter(r => r.verdict === activeFilter.value)
})

const sortedRules = computed(() => {
  if (!report.value) return []
  const order = ['FAIL', 'WARN', 'PASS', 'SKIP']
  return [...report.value.rule_results].sort((a, b) => {
    const ai = order.indexOf(a.verdict)
    const bi = order.indexOf(b.verdict)
    if (ai !== bi) return ai - bi
    return a.layer - b.layer
  })
})

const layerGroups = computed(() => {
  if (!report.value) return []
  const layers = [
    { id: 0, name: '门槛检查', icon: '🚪', rules: [] as RuleResult[] },
    { id: 1, name: '利润表信号', icon: '📈', rules: [] as RuleResult[] },
    { id: 2, name: '现金流量表', icon: '💧', rules: [] as RuleResult[] },
    { id: 3, name: '资产负债表', icon: '🏦', rules: [] as RuleResult[] },
    { id: 4, name: '交叉验证', icon: '🔗', rules: [] as RuleResult[] },
    { id: 5, name: '非财务信号', icon: '📋', rules: [] as RuleResult[] },
    { id: 6, name: '行业特有风险', icon: '🏭', rules: [] as RuleResult[] },
  ]
  for (const r of report.value.rule_results) {
    if (layers[r.layer]) layers[r.layer].rules.push(r)
  }
  return layers.map(layer => {
    const pass = layer.rules.filter(r => r.verdict === 'PASS').length
    const warn = layer.rules.filter(r => r.verdict === 'WARN').length
    const fail = layer.rules.filter(r => r.verdict === 'FAIL').length
    let status = 'pass'
    let statusColor = 'green'
    if (fail > 0) { status = 'fail'; statusColor = 'red' }
    else if (warn > 0) { status = 'warn'; statusColor = 'orange' }
    return { ...layer, pass, warn, fail, status, statusColor }
  }).filter(l => l.rules.length > 0)
})

function toggleFilter(filter: string) {
  if (activeFilter.value === filter) {
    activeFilter.value = ''
  } else {
    activeFilter.value = filter
  }
}

async function onSearch(value: string) {
  if (!value || value.length < 1) {
    searchResults.value = []
    return
  }
  try {
    const res = await fetch(`/api/v1/stock/search?keyword=${encodeURIComponent(value)}`)
    const data = await res.json()
    if (data.code === 0) {
      searchResults.value = data.data.map((s: any) => ({
        code: s.stock_code,
        name: s.stock_name,
      }))
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadWatchlistStocks() {
  if (watchlistStocks.value.length > 0) return
  try {
    const res = await watchlistApi.list()
    if (res.code === 0) {
      watchlistStocks.value = (res.data || []).map((s: any) => ({
        code: s.stock_code,
        name: s.stock_name,
      }))
    }
  } catch (e) {
    console.error('Failed to load watchlist:', e)
  }
}

function onStockSelect(code: string) {
  selectedCode.value = code
}

async function analyze() {
  if (!selectedCode.value) {
    message.warning('请先选择股票')
    return
  }
  activeFilter.value = ''
  analyzing.value = true
  loadStep.value = 0

  loadTimer = setInterval(() => {
    if (loadStep.value < 3) loadStep.value++
    else loadStep.value = 1
  }, 800)

  try {
    const res = await fetch(`/api/v1/finscan/${selectedCode.value}/analyze`)
    const data = await res.json()
    if (data.code === 0) {
      report.value = data.data
      loadStep.value = 3
      message.success('排雷分析完成')
    } else {
      message.error(data.message || '分析失败')
    }
  } catch (e: any) {
    message.error(e?.message || '网络错误')
  } finally {
    clearInterval(loadTimer)
    analyzing.value = false
  }
}

onMounted(() => {
  loadWatchlistStocks()
})

onUnmounted(() => {
  if (loadTimer) clearInterval(loadTimer)
})
</script>

<style scoped>
.finscan-page {
  width: 100%;
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  padding: 24px 28px 60px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: 0.3px;
}

.page-subtitle {
  font-size: 13px;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 80px 20px;
}

.loading-content {
  text-align: center;
  max-width: 420px;
  width: 100%;
  background: #fff;
  border-radius: 20px;
  padding: 48px 40px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.08);
}

.loading-animation {
  position: relative;
  width: 100px;
  height: 100px;
  margin: 0 auto 28px;
}

.loading-circles {
  position: absolute;
  inset: 0;
}

.circle {
  position: absolute;
  border-radius: 50%;
  border: 3px solid transparent;
}

.c1 {
  inset: 0;
  border-top-color: #3b82f6;
  animation: spin 1s linear infinite;
}

.c2 {
  inset: 10px;
  border-top-color: #8b5cf6;
  animation: spin 1.5s linear infinite reverse;
}

.c3 {
  inset: 20px;
  border-top-color: #ec4899;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 32px;
}

.loading-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 6px;
}

.loading-desc {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 28px;
}

.loading-progress {
  text-align: left;
}

.progress-bar {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  width: 60%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  border-radius: 3px;
  animation: progress-anim 2s ease-in-out infinite alternate;
}

@keyframes progress-anim {
  from { width: 30%; }
  to { width: 85%; }
}

.loading-steps {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #94a3b8;
}

.loading-steps .active {
  color: #3b82f6;
  font-weight: 600;
}

.stock-header {
  margin-bottom: 20px;
}

.stock-name-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 8px;
}

.stock-name {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.5px;
}

.stock-code {
  font-size: 16px;
  color: #64748b;
  font-weight: 500;
  font-family: 'SF Mono', monospace;
}

.stock-meta {
  display: flex;
  gap: 20px;
  color: #64748b;
  font-size: 13px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.risk-dashboard {
  display: flex;
  gap: 24px;
  margin-bottom: 28px;
  align-items: stretch;
}

.risk-gauge-card {
  width: 340px;
  flex-shrink: 0;
  border-radius: 20px;
  padding: 28px 24px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
}

.gauge-glow {
  position: absolute;
  top: -50%;
  right: -30%;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  opacity: 0.3;
  filter: blur(60px);
}

.risk-low { background: linear-gradient(135deg, #ecfdf5, #d1fae5); }
.risk-low .gauge-glow { background: #10b981; }
.risk-low .gauge-progress { stroke: #10b981; }
.risk-low .gauge-level { color: #059669; }

.risk-medium { background: linear-gradient(135deg, #fffbeb, #fef3c7); }
.risk-medium .gauge-glow { background: #f59e0b; }
.risk-medium .gauge-progress { stroke: #f59e0b; }
.risk-medium .gauge-level { color: #d97706; }

.risk-high { background: linear-gradient(135deg, #fff7ed, #ffedd5); }
.risk-high .gauge-glow { background: #f97316; }
.risk-high .gauge-progress { stroke: #f97316; }
.risk-high .gauge-level { color: #ea580c; }

.risk-very-high { background: linear-gradient(135deg, #fef2f2, #fee2e2); }
.risk-very-high .gauge-glow { background: #ef4444; }
.risk-very-high .gauge-progress { stroke: #ef4444; }
.risk-very-high .gauge-level { color: #dc2626; }

.risk-reject { background: linear-gradient(135deg, #1f2937, #111827); }
.risk-reject .gauge-glow { background: #6b7280; }
.risk-reject .gauge-progress { stroke: #6b7280; }
.risk-reject .gauge-level { color: #e5e7eb; }
.risk-reject .gauge-score, .risk-reject .gauge-unit, .risk-reject .gauge-range { color: #fff; }

.gauge-content {
  position: relative;
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
}

.gauge-ring {
  position: relative;
  width: 120px;
  height: 120px;
  flex-shrink: 0;
}

.gauge-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.gauge-bg {
  fill: none;
  stroke: rgba(255,255,255,0.5);
  stroke-width: 8;
}

.gauge-progress {
  fill: none;
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dashoffset 1s ease;
}

.gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.gauge-score {
  font-size: 36px;
  font-weight: 800;
  color: #1e293b;
  line-height: 1;
}

.gauge-unit {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.gauge-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.gauge-level {
  font-size: 22px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.level-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.8); }
}

.gauge-range {
  font-size: 12px;
  color: #64748b;
}

.gauge-scale {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #94a3b8;
  padding: 0 4px;
}

.stats-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  border: 2px solid transparent;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(0,0,0,0.08);
}

.stat-card.active {
  border-color: currentColor;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.08);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-pass { color: #16a34a; }
.stat-pass .stat-icon { background: linear-gradient(135deg, #dcfce7, #bbf7d0); }
.stat-pass.active { border-color: #22c55e; }

.stat-warn { color: #d97706; }
.stat-warn .stat-icon { background: linear-gradient(135deg, #fef3c7, #fde68a); }
.stat-warn.active { border-color: #f59e0b; }

.stat-fail { color: #dc2626; }
.stat-fail .stat-icon { background: linear-gradient(135deg, #fee2e2, #fecaca); }
.stat-fail.active { border-color: #ef4444; }

.stat-skip { color: #475569; }
.stat-skip .stat-icon { background: linear-gradient(135deg, #f1f5f9, #e2e8f0); }
.stat-skip.active { border-color: #64748b; }

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-number {
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
  color: #0f172a;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.stat-hint {
  font-size: 11px;
  color: #94a3b8;
  position: absolute;
  top: 12px;
  right: 14px;
  opacity: 0;
  transition: opacity 0.2s;
}

.stat-card:hover .stat-hint,
.stat-card.active .stat-hint {
  opacity: 1;
}

.result-section {
  background: #fff;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
  margin-bottom: 24px;
}

.section-tabs {
  display: flex;
  gap: 4px;
  padding: 16px 20px 0;
  border-bottom: 1px solid #f1f5f9;
}

.tab-item {
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-item:hover {
  color: #334155;
}

.tab-item.active {
  color: #1e293b;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}

.tab-filter {
  margin-left: auto;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 8px 8px 0 0;
  border-bottom: none;
  padding: 8px 14px;
}

.tab-filter.active {
  border-bottom: none;
}

.close-filter {
  margin-left: 8px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(59,130,246,0.2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
}

.section-content {
  padding: 24px 28px;
}

.layers-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.layer-card {
  border-radius: 14px;
  overflow: hidden;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.layer-card.layer-fail {
  background: linear-gradient(135deg, #fef2f2, #fff);
  border-color: #fecaca;
}

.layer-card.layer-warn {
  background: linear-gradient(135deg, #fffbeb, #fff);
  border-color: #fde68a;
}

.layer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: rgba(255,255,255,0.7);
  border-bottom: 1px solid #e2e8f0;
}

.layer-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.layer-icon {
  font-size: 18px;
}

.layer-rules {
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rule-card {
  display: flex;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  transition: all 0.2s;
}

.rule-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  transform: translateX(3px);
}

.rule-card-bar {
  width: 4px;
  flex-shrink: 0;
}

.rule-pass .rule-card-bar { background: #22c55e; }
.rule-warn .rule-card-bar { background: #f59e0b; }
.rule-fail .rule-card-bar { background: #ef4444; }
.rule-skip .rule-card-bar { background: #94a3b8; }

.rule-card-body {
  flex: 1;
  padding: 12px 16px;
  min-width: 0;
}

.rule-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.rule-code {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'SF Mono', monospace;
  flex-shrink: 0;
}

.rule-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  flex: 1;
}

.rule-score {
  font-size: 11px;
  font-weight: 700;
  color: #dc2626;
  background: #fee2e2;
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
}

.rule-verdict-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.badge-pass { background: #dcfce7; color: #166534; }
.badge-warn { background: #fef3c7; color: #92400e; }
.badge-fail { background: #fee2e2; color: #991b1b; }
.badge-skip { background: #f1f5f9; color: #475569; }

.badge-icon {
  font-size: 10px;
}

.rule-card-detail {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}

.rule-card.compact .rule-card-body {
  padding: 10px 14px;
}
.rule-card.compact .rule-card-detail {
  font-size: 12px;
  color: #64748b;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.legend-section {
  background: #fff;
  border-radius: 16px;
  padding: 20px 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}

.legend-title {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 14px;
}

.legend-items {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.legend-bar {
  width: 4px;
  height: 32px;
  border-radius: 2px;
  flex-shrink: 0;
}

.legend-low .legend-bar { background: linear-gradient(180deg, #22c55e, #16a34a); }
.legend-medium .legend-bar { background: linear-gradient(180deg, #f59e0b, #d97706); }
.legend-high .legend-bar { background: linear-gradient(180deg, #f97316, #ea580c); }
.legend-very-high .legend-bar { background: linear-gradient(180deg, #ef4444, #dc2626); }
.legend-reject .legend-bar { background: linear-gradient(180deg, #6b7280, #374151); }

.legend-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.legend-label {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.legend-range {
  font-size: 11px;
  color: #64748b;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-illustration {
  font-size: 80px;
  margin-bottom: 24px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.empty-title {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 10px;
}

.empty-desc {
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 36px;
}

.empty-features {
  display: flex;
  justify-content: center;
  gap: 24px;
  flex-wrap: wrap;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}

.feature-icon {
  font-size: 28px;
}

@media (max-width: 1100px) {
  .risk-dashboard {
    flex-direction: column;
  }
  .risk-gauge-card {
    width: 100%;
  }
  .legend-items {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 640px) {
  .finscan-page {
    padding: 16px;
  }
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .legend-items {
    grid-template-columns: repeat(2, 1fr);
  }
  .stock-name {
    font-size: 22px;
  }
  .section-content {
    padding: 16px;
  }
}
</style>
