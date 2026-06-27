<template>
  <div class="finscan-page">
    <div class="page-header">
      <h3 class="page-title">财报排雷</h3>
      <div class="header-actions">
        <a-select
          v-model:value="selectedCode"
          show-search
          placeholder="选择自选股票或搜索"
          style="width: 220px"
          :filter-option="false"
          @search="onSearch"
          @change="onStockSelect"
          @focus="loadWatchlistStocks"
        >
          <a-select-option v-for="s in allOptions" :key="s.code" :value="s.code">
            {{ s.name }} ({{ s.code }})
          </a-select-option>
        </a-select>
        <a-button type="primary" :loading="analyzing" @click="analyze">
          开始排雷
        </a-button>
      </div>
    </div>

    <a-spin :spinning="analyzing">
      <div v-if="report" class="report-content">
        <div class="stock-info-bar">
          <span class="stock-name">{{ report.stock_name }}</span>
          <span class="stock-code">{{ report.stock_code }}</span>
          <span class="report-year">{{ report.report_year }}年年报</span>
        </div>

        <div class="risk-dashboard">
          <div class="risk-gauge" :class="riskLevelClass">
            <div class="gauge-score">{{ report.total_score }}</div>
            <div class="gauge-label">风险评分</div>
            <div class="gauge-level">{{ riskLevelText }}</div>
          </div>
          <div class="risk-stats">
            <div
              class="stat-card stat-pass"
              :class="{ active: activeFilter === 'PASS' }"
              @click="toggleFilter('PASS')"
            >
              <div class="stat-number">{{ report.n_pass }}</div>
              <div class="stat-label">通过</div>
              <div v-if="activeFilter === 'PASS'" class="stat-filter-tip">点击取消筛选</div>
            </div>
            <div
              class="stat-card stat-warn"
              :class="{ active: activeFilter === 'WARN' }"
              @click="toggleFilter('WARN')"
            >
              <div class="stat-number">{{ report.n_warn }}</div>
              <div class="stat-label">警告</div>
              <div v-if="activeFilter === 'WARN'" class="stat-filter-tip">点击取消筛选</div>
            </div>
            <div
              class="stat-card stat-fail"
              :class="{ active: activeFilter === 'FAIL' }"
              @click="toggleFilter('FAIL')"
            >
              <div class="stat-number">{{ report.n_fail }}</div>
              <div class="stat-label">失败</div>
              <div v-if="activeFilter === 'FAIL'" class="stat-filter-tip">点击取消筛选</div>
            </div>
            <div
              class="stat-card stat-skip"
              :class="{ active: activeFilter === 'SKIP' }"
              @click="toggleFilter('SKIP')"
            >
              <div class="stat-number">{{ report.n_skip }}</div>
              <div class="stat-label">跳过</div>
              <div v-if="activeFilter === 'SKIP'" class="stat-filter-tip">点击取消筛选</div>
            </div>
          </div>
        </div>

        <div v-if="activeFilter" class="filter-notice">
          <a-alert
            :message="`当前筛选：${filterLabel}（${filteredResults.length}条）`"
            type="info"
            show-icon
            :closable="true"
            @close="activeFilter = ''"
          />
        </div>

        <a-card class="result-card" :title="activeFilter ? '筛选结果' : '风险信号（按层级）'">
          <template v-if="activeFilter">
            <div class="rule-list">
              <div
                v-for="rule in filteredResults"
                :key="rule.code"
                class="rule-item"
                :class="`rule-${rule.verdict.toLowerCase()}`"
              >
                <div class="rule-header">
                  <span class="rule-code">{{ rule.code }}</span>
                  <span class="rule-name">{{ rule.name }}</span>
                  <a-tag :color="getVerdictColor(rule.verdict)" class="rule-verdict-tag">
                    {{ getVerdictLabel(rule.verdict) }}
                  </a-tag>
                  <span v-if="rule.score_added > 0" class="rule-score">扣{{ rule.score_added }}分</span>
                </div>
                <div class="rule-detail">{{ rule.detail }}</div>
                <div v-if="rule.raw_values && Object.keys(rule.raw_values).length" class="rule-raw-values">
                  <span class="raw-label">关键数据：</span>
                  <span v-for="(val, key) in rule.raw_values" :key="key" class="raw-item">
                    {{ formatRawKey(key) }}: {{ formatRawValue(val) }}
                  </span>
                </div>
              </div>
            </div>
            <a-empty v-if="filteredResults.length === 0" description="暂无该类型的检查项" />
          </template>

          <template v-else>
            <a-alert
              v-if="report.risk_level === 'REJECT'"
              message="一票否决"
              description="审计意见非标准无保留或未按时披露，建议直接排除"
              type="error"
              show-icon
              class="reject-alert"
            />

            <a-collapse v-model:activeKey="activeKeys">
              <a-collapse-panel key="layer0" header="门槛检查 (Layer 0)">
                <template #extra>
                  <a-badge :status="getLayerStatus(0)" :text="getLayerSummary(0)" />
                </template>
                <RuleList :rules="layer0Rules" />
              </a-collapse-panel>

              <a-collapse-panel key="layer1" header="利润表信号 (Layer 1)">
                <template #extra>
                  <a-badge :status="getLayerStatus(1)" :text="getLayerSummary(1)" />
                </template>
                <RuleList :rules="layer1Rules" />
              </a-collapse-panel>

              <a-collapse-panel key="layer2" header="现金流量表信号 (Layer 2)">
                <template #extra>
                  <a-badge :status="getLayerStatus(2)" :text="getLayerSummary(2)" />
                </template>
                <RuleList :rules="layer2Rules" />
              </a-collapse-panel>

              <a-collapse-panel key="layer3" header="资产负债表信号 (Layer 3)">
                <template #extra>
                  <a-badge :status="getLayerStatus(3)" :text="getLayerSummary(3)" />
                </template>
                <RuleList :rules="layer3Rules" />
              </a-collapse-panel>

              <a-collapse-panel key="layer4" header="交叉验证 (Layer 4)">
                <template #extra>
                  <a-badge :status="getLayerStatus(4)" :text="getLayerSummary(4)" />
                </template>
                <RuleList :rules="layer4Rules" />
              </a-collapse-panel>

              <a-collapse-panel key="layer5" header="非财务信号 (Layer 5)">
                <template #extra>
                  <a-badge :status="getLayerStatus(5)" :text="getLayerSummary(5)" />
                </template>
                <RuleList :rules="layer5Rules" />
              </a-collapse-panel>

              <a-collapse-panel key="layer6" header="行业特有风险 (Layer 6)">
                <template #extra>
                  <a-badge :status="getLayerStatus(6)" :text="getLayerSummary(6)" />
                </template>
                <RuleList :rules="layer6Rules" />
              </a-collapse-panel>
            </a-collapse>
          </template>
        </a-card>
      </div>

      <div v-else-if="!analyzing && !selectedCode" class="empty-state">
        <div class="empty-icon">🔍</div>
        <div class="empty-text">输入股票代码，开始排雷分析</div>
        <div class="empty-desc">基于《手把手教你读财报》30条排雷规则</div>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted } from 'vue'
import { message } from 'ant-design-vue'
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

const selectedCode = ref<string>('')
const searchResults = ref<SearchResult[]>([])
const watchlistStocks = ref<SearchResult[]>([])
const analyzing = ref(false)
const report = ref<Report | null>(null)
const activeKeys = ref(['layer0', 'layer1'])
const activeFilter = ref<string>('')

const allOptions = computed(() => {
  if (searchResults.value.length > 0) {
    return searchResults.value
  }
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

const layer0Rules = computed(() => filterByLayer(0))
const layer1Rules = computed(() => filterByLayer(1))
const layer2Rules = computed(() => filterByLayer(2))
const layer3Rules = computed(() => filterByLayer(3))
const layer4Rules = computed(() => filterByLayer(4))
const layer5Rules = computed(() => filterByLayer(5))
const layer6Rules = computed(() => filterByLayer(6))

function filterByLayer(layer: number) {
  return report.value?.rule_results.filter(r => r.layer === layer) || []
}

function toggleFilter(filter: string) {
  if (activeFilter.value === filter) {
    activeFilter.value = ''
  } else {
    activeFilter.value = filter
  }
}

function getVerdictColor(verdict: string): string {
  const map: Record<string, string> = {
    'PASS': 'success',
    'WARN': 'warning',
    'FAIL': 'error',
    'SKIP': 'default',
  }
  return map[verdict] || 'default'
}

function getVerdictLabel(verdict: string): string {
  const map: Record<string, string> = {
    'PASS': '✓ 通过',
    'WARN': '⚠ 警告',
    'FAIL': '✗ 失败',
    'SKIP': '○ 跳过',
  }
  return map[verdict] || verdict
}

function formatRawKey(key: string): string {
  const map: Record<string, string> = {
    'gm_cur': '当前毛利率',
    'gm_yoy': '毛利率同比',
    'gm_vs_peer': 'vs同行',
    'signals': '信号数',
    'n_signals': '信号数量',
    'years': '年数',
    'neg_years': '负年数',
    'max_consecutive': '最长连续',
    'ar_growth': '应收增速',
    'rev_growth': '营收增速',
    'ratio': '比率',
    'inv_turn_change': '存货周转率变化',
    'gm_change': '毛利率变化',
    'is_combo': '是否组合',
    'lt_amort': '长期待摊',
    'yoy_change': '同比变化',
    'bad_debt_ratio': '坏账计提比例',
    'peer_ratio': '同行比例',
    'years_below_1': '净现比<1年数',
    'years_below': '低于阈值年数',
    'years_abnormal': '异常年数',
    'core_profit': '核心利润',
    'net_profit': '净利润',
    'divergence': '背离度',
    'current_ratio': '当前费用率',
    'avg_3yr': '3年均值',
    'drop': '下降幅度',
    'total_impair': '减值总额',
    'impair_yoy': '减值同比',
    'impair_to_profit': '占净利润比',
    'cash': '货币资金',
    'interest_debt': '有息负债',
    'audit_result': '审计意见',
  }
  return map[key] || key
}

function formatRawValue(val: any): string {
  if (val === null || val === undefined) return 'N/A'
  if (typeof val === 'boolean') return val ? '是' : '否'
  if (Array.isArray(val)) return val.join(', ')
  if (typeof val === 'number') {
    if (Math.abs(val) > 1e8) return (val / 1e8).toFixed(2) + '亿'
    if (Math.abs(val) > 1e4) return (val / 1e4).toFixed(2) + '万'
    return val.toFixed(2)
  }
  return String(val).slice(0, 30)
}

function getLayerStatus(layer: number) {
  const rules = filterByLayer(layer)
  if (!rules.length) return 'default'
  const hasFail = rules.some(r => r.verdict === 'FAIL')
  const hasWarn = rules.some(r => r.verdict === 'WARN')
  if (hasFail) return 'error'
  if (hasWarn) return 'warning'
  return 'success'
}

function getLayerSummary(layer: number) {
  const rules = filterByLayer(layer)
  const pass = rules.filter(r => r.verdict === 'PASS').length
  const warn = rules.filter(r => r.verdict === 'WARN').length
  const fail = rules.filter(r => r.verdict === 'FAIL').length
  const skip = rules.filter(r => r.verdict === 'SKIP').length
  const parts = []
  if (fail > 0) parts.push(`${fail}失败`)
  if (warn > 0) parts.push(`${warn}警告`)
  if (pass > 0) parts.push(`${pass}通过`)
  if (skip > 0) parts.push(`${skip}跳过`)
  return parts.join(' ')
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
  try {
    const res = await fetch(`/api/v1/finscan/${selectedCode.value}/analyze`)
    const data = await res.json()
    if (data.code === 0) {
      report.value = data.data
      message.success('排雷分析完成')
    } else {
      message.error(data.message || '分析失败')
    }
  } catch (e: any) {
    message.error(e?.message || '网络错误')
  } finally {
    analyzing.value = false
  }
}

onMounted(() => {
  loadWatchlistStocks()
})
</script>

<script lang="ts">
const RuleList = {
  props: ['rules'],
  setup(props: { rules: RuleResult[] }) {
    return () => h('div', { class: 'rule-list' },
      props.rules.map(rule => h('div', {
        class: ['rule-item', `rule-${rule.verdict.toLowerCase()}`],
      }, [
        h('div', { class: 'rule-header' }, [
          h('span', { class: 'rule-code' }, rule.code),
          h('span', { class: 'rule-name' }, rule.name),
          h('span', {
            class: ['rule-verdict', `verdict-${rule.verdict.toLowerCase()}`],
          }, {
            'PASS': '✓ 通过',
            'WARN': '⚠ 警告',
            'FAIL': '✗ 失败',
            'SKIP': '○ 跳过',
          }[rule.verdict] || rule.verdict),
          rule.score_added > 0 ? h('span', { class: 'rule-score' }, `扣${rule.score_added}分`) : null,
        ]),
        h('div', { class: 'rule-detail' }, rule.detail),
      ]))
    )
  }
}
export default {}
</script>

<style scoped>
.finscan-page {
  width: 100%;
  padding: 24px;
  background: #f5f7fa;
  min-height: 600px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 0 4px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  letter-spacing: 0.5px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.stock-info-bar {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
  padding: 0 4px;
}

.stock-name {
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
}

.stock-code {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

.report-year {
  font-size: 13px;
  color: #9ca3af;
  margin-left: auto;
  background: #e5e7eb;
  padding: 4px 12px;
  border-radius: 12px;
}

.risk-dashboard {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
  align-items: stretch;
}

.risk-gauge {
  width: 180px;
  height: 180px;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  text-align: center;
  transition: all 0.3s;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.risk-gauge::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
  animation: shimmer 3s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
  100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
}

.risk-gauge.risk-low {
  background: linear-gradient(135deg, #10b981, #34d399);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.35);
}

.risk-gauge.risk-medium {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  box-shadow: 0 8px 24px rgba(245, 158, 11, 0.35);
}

.risk-gauge.risk-high {
  background: linear-gradient(135deg, #f97316, #fb923c);
  box-shadow: 0 8px 24px rgba(249, 115, 22, 0.35);
}

.risk-gauge.risk-very-high {
  background: linear-gradient(135deg, #ef4444, #f87171);
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.35);
}

.risk-gauge.risk-reject {
  background: linear-gradient(135deg, #1f2937, #374151);
  box-shadow: 0 8px 24px rgba(31, 41, 55, 0.35);
}

.gauge-score {
  font-size: 48px;
  font-weight: 800;
  line-height: 1;
  text-shadow: 0 2px 8px rgba(0,0,0,0.2);
  z-index: 1;
}

.gauge-label {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 6px;
  z-index: 1;
}

.gauge-level {
  font-size: 14px;
  font-weight: 600;
  margin-top: 10px;
  padding: 4px 16px;
  background: rgba(255,255,255,0.2);
  backdrop-filter: blur(10px);
  border-radius: 14px;
  z-index: 1;
}

.risk-stats {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  padding: 20px 16px;
  border-radius: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  background: #fff;
  border: 2px solid transparent;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.08);
}

.stat-card.active {
  border-width: 2px;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0,0,0,0.1);
}

.stat-pass {
  background: linear-gradient(135deg, #f0fdf4, #dcfce7);
}
.stat-pass.active {
  border-color: #22c55e;
}

.stat-warn {
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
}
.stat-warn.active {
  border-color: #f59e0b;
}

.stat-fail {
  background: linear-gradient(135deg, #fef2f2, #fee2e2);
}
.stat-fail.active {
  border-color: #ef4444;
}

.stat-skip {
  background: linear-gradient(135deg, #f9fafb, #f3f4f6);
}
.stat-skip.active {
  border-color: #6b7280;
}

.stat-number {
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
  margin-bottom: 6px;
}

.stat-pass .stat-number { color: #16a34a; }
.stat-warn .stat-number { color: #d97706; }
.stat-fail .stat-number { color: #dc2626; }
.stat-skip .stat-number { color: #6b7280; }

.stat-label {
  font-size: 14px;
  font-weight: 600;
  color: #4b5563;
}

.stat-filter-tip {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 6px;
  opacity: 0.8;
}

.filter-notice {
  margin-bottom: 16px;
}

.result-card {
  border-radius: 16px !important;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
  border: none !important;
}

.result-card :deep(.ant-card-head) {
  border-bottom: 1px solid #f3f4f6 !important;
  font-weight: 600;
}

.reject-alert {
  margin-bottom: 16px;
  border-radius: 10px;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rule-item {
  padding: 16px 20px;
  border-radius: 12px;
  border-left: 4px solid;
  transition: all 0.2s;
  position: relative;
}

.rule-item:hover {
  transform: translateX(4px);
}

.rule-pass {
  background: linear-gradient(135deg, #f0fdf4, #fff);
  border-color: #22c55e;
}

.rule-warn {
  background: linear-gradient(135deg, #fffbeb, #fff);
  border-color: #f59e0b;
}

.rule-fail {
  background: linear-gradient(135deg, #fef2f2, #fff);
  border-color: #ef4444;
}

.rule-skip {
  background: linear-gradient(135deg, #f9fafb, #fff);
  border-color: #9ca3af;
}

.rule-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.rule-code {
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
  background: #f3f4f6;
  padding: 3px 8px;
  border-radius: 6px;
  font-family: 'SF Mono', monospace;
}

.rule-name {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.rule-verdict-tag {
  margin-left: auto;
  font-weight: 500;
}

.rule-verdict {
  font-size: 13px;
  font-weight: 700;
  margin-left: auto;
}

.verdict-pass { color: #16a34a; }
.verdict-warn { color: #d97706; }
.verdict-fail { color: #dc2626; }
.verdict-skip { color: #6b7280; }

.rule-score {
  font-size: 12px;
  color: #dc2626;
  font-weight: 700;
  background: #fee2e2;
  padding: 2px 8px;
  border-radius: 6px;
}

.rule-detail {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
}

.rule-raw-values {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e5e7eb;
  font-size: 12px;
  color: #6b7280;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.raw-label {
  font-weight: 600;
  color: #4b5563;
}

.raw-item {
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'SF Mono', monospace;
}

.empty-state {
  text-align: center;
  padding: 100px 20px;
}

.empty-icon {
  font-size: 72px;
  margin-bottom: 20px;
  opacity: 0.6;
}

.empty-text {
  font-size: 18px;
  color: #6b7280;
  font-weight: 500;
}

.empty-desc {
  font-size: 14px;
  color: #9ca3af;
  margin-top: 8px;
}

@media (max-width: 900px) {
  .risk-dashboard {
    flex-direction: column;
  }
  .risk-gauge {
    width: 100%;
    height: 140px;
  }
  .risk-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
