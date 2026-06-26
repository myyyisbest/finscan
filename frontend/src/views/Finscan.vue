<template>
  <div class="finscan-page">
    <div class="page-header">
      <h3 class="page-title">财报排雷</h3>
      <div class="header-actions">
        <a-select
          v-model:value="selectedCode"
          show-search
          placeholder="输入股票代码或名称搜索"
          style="width: 200px"
          :filter-option="false"
          @search="onSearch"
          @change="onStockSelect"
        >
          <a-select-option v-for="s in searchResults" :key="s.code" :value="s.code">
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
        <!-- 风险仪表盘 -->
        <div class="risk-dashboard">
          <div class="risk-gauge" :class="riskLevelClass">
            <div class="gauge-score">{{ report.total_score }}</div>
            <div class="gauge-label">风险评分</div>
            <div class="gauge-level">{{ riskLevelText }}</div>
          </div>
          <div class="risk-stats">
            <div class="stat-card stat-pass">
              <div class="stat-number">{{ report.n_pass }}</div>
              <div class="stat-label">通过</div>
            </div>
            <div class="stat-card stat-warn">
              <div class="stat-number">{{ report.n_warn }}</div>
              <div class="stat-label">警告</div>
            </div>
            <div class="stat-card stat-fail">
              <div class="stat-number">{{ report.n_fail }}</div>
              <div class="stat-label">失败</div>
            </div>
            <div class="stat-card stat-skip">
              <div class="stat-number">{{ report.n_skip }}</div>
              <div class="stat-label">跳过</div>
            </div>
            <div v-if="report.combo_bonus > 0" class="stat-card stat-combo">
              <div class="stat-number">+{{ report.combo_bonus }}</div>
              <div class="stat-label">组合加分</div>
            </div>
          </div>
        </div>

        <!-- 风险信号 -->
        <a-card class="result-card" title="风险信号">
          <a-alert
            v-if="report.risk_level === 'REJECT'"
            message="一票否决"
            description="审计意见非标准无保留或未按时披露，建议直接排除"
            type="error"
            show-icon
            class="reject-alert"
          />

          <a-collapse v-model:activeKey="activeKeys">
            <!-- Layer 0: 门槛检查 -->
            <a-collapse-panel key="layer0" header="门槛检查 (2条)">
              <template #extra>
                <a-badge :status="getLayer0Status()" :text="getLayer0Summary()" />
              </template>
              <RuleList :rules="layer0Rules" />
            </a-collapse-panel>

            <!-- Layer 1: 利润表 -->
            <a-collapse-panel key="layer1" header="利润表信号 (6条)">
              <template #extra>
                <a-badge :status="getLayerStatus(1)" :text="getLayerSummary(1)" />
              </template>
              <RuleList :rules="layer1Rules" />
            </a-collapse-panel>

            <!-- Layer 2: 现金流量表 -->
            <a-collapse-panel key="layer2" header="现金流量表信号 (3条)">
              <template #extra>
                <a-badge :status="getLayerStatus(2)" :text="getLayerSummary(2)" />
              </template>
              <RuleList :rules="layer2Rules" />
            </a-collapse-panel>

            <!-- Layer 3: 资产负债表 -->
            <a-collapse-panel key="layer3" header="资产负债表信号 (5条)">
              <template #extra>
                <a-badge :status="getLayerStatus(3)" :text="getLayerSummary(3)" />
              </template>
              <RuleList :rules="layer3Rules" />
            </a-collapse-panel>

            <!-- Layer 4: 交叉验证 -->
            <a-collapse-panel key="layer4" header="交叉验证 (5条)">
              <template #extra>
                <a-badge :status="getLayerStatus(4)" :text="getLayerSummary(4)" />
              </template>
              <RuleList :rules="layer4Rules" />
            </a-collapse-panel>

            <!-- Layer 5: 非财务信号 -->
            <a-collapse-panel key="layer5" header="非财务信号 (6条)">
              <template #extra>
                <a-badge :status="getLayerStatus(5)" :text="getLayerSummary(5)" />
              </template>
              <RuleList :rules="layer5Rules" />
            </a-collapse-panel>

            <!-- Layer 6: 行业特有 -->
            <a-collapse-panel key="layer6" header="行业特有风险 (2条)">
              <template #extra>
                <a-badge :status="getLayerStatus(6)" :text="getLayerSummary(6)" />
              </template>
              <RuleList :rules="layer6Rules" />
            </a-collapse-panel>
          </a-collapse>
        </a-card>
      </div>

      <div v-else-if="!analyzing && !selectedCode" class="empty-state">
        <div class="empty-icon">🔍</div>
        <div class="empty-text">输入股票代码，开始排雷分析</div>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { message } from 'ant-design-vue'

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
const analyzing = ref(false)
const report = ref<Report | null>(null)
const activeKeys = ref(['layer0', 'layer1'])

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
  return `${pass}通过 ${warn}警告 ${fail}失败 ${skip}跳过`
}

function getLayer0Status() {
  const rules = layer0Rules.value
  const hasFail = rules.some(r => r.verdict === 'FAIL')
  return hasFail ? 'error' : 'success'
}

function getLayer0Summary() {
  const rules = layer0Rules.value
  const pass = rules.filter(r => r.verdict === 'PASS').length
  const fail = rules.filter(r => r.verdict === 'FAIL').length
  return `${pass}通过 ${fail}失败`
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

function onStockSelect(code: string) {
  selectedCode.value = code
}

async function analyze() {
  if (!selectedCode.value) {
    message.warning('请先选择股票')
    return
  }
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
  padding: 20px;
  background: #fff;
  border-radius: 4px;
  min-height: 600px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #1d4ed8;
  padding-bottom: 12px;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1d4ed8;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.risk-dashboard {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.risk-gauge {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  text-align: center;
  transition: all 0.3s;
}

.risk-gauge.risk-low {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  box-shadow: 0 4px 12px rgba(82, 196, 26, 0.3);
}

.risk-gauge.risk-medium {
  background: linear-gradient(135deg, #faad14, #ffc53d);
  box-shadow: 0 4px 12px rgba(250, 173, 20, 0.3);
}

.risk-gauge.risk-high {
  background: linear-gradient(135deg, #fa8c16, #ffa940);
  box-shadow: 0 4px 12px rgba(250, 140, 22, 0.3);
}

.risk-gauge.risk-very-high {
  background: linear-gradient(135deg, #f5222d, #ff7875);
  box-shadow: 0 4px 12px rgba(245, 34, 45, 0.3);
}

.risk-gauge.risk-reject {
  background: linear-gradient(135deg, #000, #333);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.gauge-score {
  font-size: 42px;
  font-weight: 700;
  line-height: 1;
}

.gauge-label {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 4px;
}

.gauge-level {
  font-size: 14px;
  font-weight: 600;
  margin-top: 8px;
  padding: 2px 12px;
  background: rgba(255,255,255,0.2);
  border-radius: 10px;
}

.risk-stats {
  flex: 1;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 80px;
  padding: 16px;
  border-radius: 8px;
  text-align: center;
}

.stat-pass {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
}

.stat-warn {
  background: #fffbe6;
  border: 1px solid #ffe58f;
}

.stat-fail {
  background: #fff2f0;
  border: 1px solid #ffccc7;
}

.stat-skip {
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
}

.stat-combo {
  background: #f0f5ff;
  border: 1px solid #adc6ff;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.result-card {
  margin-bottom: 20px;
}

.reject-alert {
  margin-bottom: 16px;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rule-item {
  padding: 12px 16px;
  border-radius: 6px;
  border-left: 3px solid;
}

.rule-pass {
  background: #f6ffed;
  border-color: #52c41a;
}

.rule-warn {
  background: #fffbe6;
  border-color: #faad14;
}

.rule-fail {
  background: #fff2f0;
  border-color: #f5222d;
}

.rule-skip {
  background: #f5f5f5;
  border-color: #d9d9d9;
}

.rule-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.rule-code {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
}

.rule-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.rule-verdict {
  font-size: 12px;
  font-weight: 600;
  margin-left: auto;
}

.verdict-pass { color: #52c41a; }
.verdict-warn { color: #faad14; }
.verdict-fail { color: #f5222d; }
.verdict-skip { color: #999; }

.rule-score {
  font-size: 12px;
  color: #f5222d;
  font-weight: 600;
}

.rule-detail {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
  color: #999;
}
</style>
