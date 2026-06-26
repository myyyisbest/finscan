<template>
  <div class="dupont-analysis">
    <div class="dupont-header">
      <h3 class="dupont-title">杜邦分析结构图</h3>
      <div class="report-pager">
        <a-button
          type="text"
          size="small"
          :disabled="!canPrev"
          @click="prevReport"
        >
          <template #icon><left-outlined /></template>
        </a-button>
        <span class="current-period">{{ currentReportName || '请选择报告期' }}</span>
        <a-button
          type="text"
          size="small"
          :disabled="!canNext"
          @click="nextReport"
        >
          <template #icon><right-outlined /></template>
        </a-button>
      </div>
    </div>

    <a-spin :spinning="loading">
      <div v-if="!loading && displayNodes.length" class="dupont-tree">
        <div class="tree-canvas" :style="`transform: scale(${zoom})`">
          <!-- 顶层 ROE -->
          <div class="node-root">
            <div class="node-card node-card-root" @click="toggleNode('roe')">
              <div class="node-label">ROE 净资产收益率</div>
              <div class="node-value">{{ formatVal(roeNode?.value) }}<span class="node-unit">{{ roeNode?.unit }}</span></div>
              <div v-if="roeNode?.yoy !== null && roeNode?.yoy !== undefined" class="node-yoy" :class="roeNode.yoy >= 0 ? 'yoy-up' : 'yoy-down'">
                同比 {{ roeNode.yoy >= 0 ? '+' : '' }}{{ roeNode.yoy }}%
              </div>
            </div>
          </div>

          <!-- 公式连接 -->
          <div class="formula-line">
            <span class="formula-symbol">=</span>
          </div>

          <!-- 第二层：三个一级驱动 -->
          <div class="level level-1">
            <div
              v-for="(child, idx) in (roeNode?.children || [])"
              :key="child.key"
              class="level-1-item"
            >
              <div class="op-symbol" v-if="idx > 0">×</div>
              <div class="node-card node-card-l1" @click="toggleNode(child.key)">
                <div class="node-label">{{ child.name }}</div>
                <div class="node-value">{{ formatVal(child.value) }}<span class="node-unit">{{ child.unit }}</span></div>
                <div v-if="child.yoy !== null && child.yoy !== undefined" class="node-yoy" :class="child.yoy >= 0 ? 'yoy-up' : 'yoy-down'">
                  同比 {{ child.yoy >= 0 ? '+' : '' }}{{ child.yoy }}%
                </div>
              </div>
            </div>
          </div>

          <!-- 展开的子树 -->
          <template v-for="(child, idx) in (roeNode?.children || [])" :key="`sub-${child.key}`">
            <div v-if="expandedNodes.has(child.key) && child.children?.length" class="subtree-wrapper">
              <div class="connector"></div>
              <div class="level level-2">
                <div
                  v-for="sub in child.children"
                  :key="sub.key"
                  class="level-2-item"
                >
                  <div class="node-card node-card-l2" @click="toggleNode(sub.key)">
                    <div class="node-label">{{ sub.name }}</div>
                    <div class="node-value">{{ formatVal(sub.value) }}<span class="node-unit">{{ sub.unit }}</span></div>
                    <div v-if="sub.yoy !== null && sub.yoy !== undefined" class="node-yoy" :class="sub.yoy >= 0 ? 'yoy-up' : 'yoy-down'">
                      同比 {{ sub.yoy >= 0 ? '+' : '' }}{{ sub.yoy }}%
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- 节点详情面板（点击节点显示） -->
        <div v-if="selectedNode" class="node-detail-panel">
          <a-card size="small" :title="selectedNode.name">
            <template #extra>
              <a-tag color="blue">{{ selectedNode.formula }}</a-tag>
            </template>
            <div class="detail-row">
              <span class="detail-label">当前值：</span>
              <span class="detail-value">{{ formatVal(selectedNode.value) }} {{ selectedNode.unit }}</span>
            </div>
            <div v-if="selectedNode.yoy !== null && selectedNode.yoy !== undefined" class="detail-row">
              <span class="detail-label">同比变化：</span>
              <span :class="selectedNode.yoy >= 0 ? 'yoy-up' : 'yoy-down'">
                {{ selectedNode.yoy >= 0 ? '+' : '' }}{{ selectedNode.yoy }}%
              </span>
            </div>
            <div class="detail-chart">
              <div class="chart-title">近{{ chartHistory.length }}期趋势</div>
              <div class="chart-bars">
                <div
                  v-for="(v, i) in chartHistory"
                  :key="i"
                  class="bar-item"
                >
                  <div class="bar-wrapper">
                    <div
                      class="bar-fill"
                      :style="getBarStyle(v, chartHistory, selectedNode?.is_pct)"
                      :title="`${v !== null ? formatVal(v) : '-'}${selectedNode?.unit || ''}`"
                    >
                      <span class="bar-value">{{ v !== null ? formatVal(v) : '-' }}</span>
                    </div>
                  </div>
                  <div class="bar-label">{{ formatPeriod(chartLabels[i]) }}</div>
                </div>
              </div>
            </div>
          </a-card>
        </div>

        <!-- 缩放控制 -->
        <div class="zoom-controls">
          <a-button-group>
            <a-button @click="zoomOut" :disabled="zoom <= 0.6"><minus-outlined /></a-button>
            <a-button @click="resetZoom">{{ Math.round(zoom * 100) }}%</a-button>
            <a-button @click="zoomIn" :disabled="zoom >= 1.5"><plus-outlined /></a-button>
          </a-button-group>
        </div>
      </div>
      <a-empty v-else-if="!loading" description="暂无数据，请先采集该股票数据" />
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { LeftOutlined, RightOutlined, PlusOutlined, MinusOutlined } from '@ant-design/icons-vue'
import { financeApi, type DupontNode } from '@/api/finance'

const props = defineProps<{
  stockCode: string
}>()

const loading = ref(false)
const rawNodes = ref<DupontNode[]>([])
const reportDates = ref<string[]>([])
const reportNames = ref<string[]>([])
const currentReportIdx = ref(0)
const expandedNodes = ref<Set<string>>(new Set(['roe']))
const selectedKey = ref<string>('roe')
const zoom = ref(1)

function getNodeAtIdx(nodes: DupontNode[], idx: number): DupontNode[] {
  return nodes.map((node) => {
    const hist = node.history || []
    const n = hist.length
    const valIdx = n - 1 - idx
    const currentVal = valIdx >= 0 && valIdx < n ? hist[valIdx] : null
    let yoy: number | null = null
    if (valIdx >= 1 && hist[valIdx - 1] !== null && hist[valIdx - 1] !== 0 && hist[valIdx] !== null) {
      yoy = round2((hist[valIdx] - hist[valIdx - 1]) / Math.abs(hist[valIdx - 1]) * 100)
    }
    const children = node.children ? getNodeAtIdx(node.children, idx) : []
    return {
      ...node,
      value: currentVal,
      yoy,
      children,
    }
  })
}

function round2(v: number): number {
  return Math.round(v * 100) / 100
}

const displayNodes = computed(() => {
  if (!rawNodes.value.length) return []
  return getNodeAtIdx(rawNodes.value, currentReportIdx.value)
})

const roeNode = computed(() => displayNodes.value[0])

const selectedNode = computed(() => {
  const found = findNode(displayNodes.value, selectedKey.value)
  return found || displayNodes.value[0] || null
})

const chartHistory = computed(() => {
  const node = selectedNode.value
  if (!node || !node.history) return []
  const hist = node.history
  const n = hist.length
  const endIdx = n - currentReportIdx.value
  return hist.slice(0, endIdx)
})

const chartLabels = computed(() => {
  if (!reportNames.value.length) return []
  const names = [...reportNames.value].reverse()
  const n = names.length
  const endIdx = n - currentReportIdx.value
  return names.slice(0, endIdx)
})

const currentReportName = computed(() => {
  if (!reportNames.value.length) return ''
  return reportNames.value[currentReportIdx.value] || ''
})

const canPrev = computed(() => currentReportIdx.value < reportDates.value.length - 1)
const canNext = computed(() => currentReportIdx.value > 0)

function prevReport() {
  if (canPrev.value) {
    currentReportIdx.value++
  }
}

function nextReport() {
  if (canNext.value) {
    currentReportIdx.value--
  }
}

function toggleNode(key: string) {
  const roe = roeNode.value
  if (roe) {
    const child = roe.children?.find((c) => c.key === key)
    if (child) {
      if (expandedNodes.value.has(key)) {
        expandedNodes.value.delete(key)
      } else {
        expandedNodes.value.add(key)
      }
      return
    }
  }
  selectedKey.value = key
}

function findNode(list: DupontNode[], key: string): DupontNode | null {
  for (const n of list) {
    if (n.key === key) return n
    const sub = findNode(n.children || [], key)
    if (sub) return sub
  }
  return null
}

function formatVal(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-'
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(2)
}

function formatPeriod(name: string | undefined): string {
  if (!name) return ''
  return name.replace(/报告|报/g, '')
}

function getBarStyle(v: number | null, history: (number | null)[], isPct: boolean) {
  if (v === null) return { height: '0%' }
  const nums = history.filter((x): x is number => x !== null && !isNaN(x))
  if (!nums.length) return { height: '0%' }
  const max = Math.max(...nums.map(Math.abs))
  const min = Math.min(...nums)
  const range = max - min || 1
  let pct = 0
  if (isPct || nums.some((n) => Math.abs(n) < 100)) {
    pct = Math.abs(v) / Math.max(max, 1) * 100
  } else {
    pct = ((v - min) / range) * 100
  }
  const color = v >= 0 ? '#1890ff' : '#ff4d4f'
  return { height: `${Math.min(100, Math.max(5, pct))}%`, background: color }
}

function zoomIn() { zoom.value = Math.min(1.5, zoom.value + 0.1) }
function zoomOut() { zoom.value = Math.max(0.6, zoom.value - 0.1) }
function resetZoom() { zoom.value = 1 }

async function loadData() {
  if (!props.stockCode) return
  loading.value = true
  try {
    const res = await financeApi.getDupont(props.stockCode, 8)
    if (res.code === 0 && res.data) {
      rawNodes.value = res.data.nodes || []
      reportDates.value = res.data.report_dates || []
      reportNames.value = res.data.report_names || []
      selectedKey.value = 'roe'
      expandedNodes.value = new Set(['roe'])
    }
  } finally {
    loading.value = false
  }
}

watch(() => props.stockCode, (val) => {
  if (val) {
    currentReportIdx.value = 0
    loadData()
  }
}, { immediate: true })
</script>

<style scoped>
.dupont-analysis {
  position: relative;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 16px;
  min-height: 600px;
}

.dupont-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #1d4ed8;
  padding-bottom: 8px;
  margin-bottom: 16px;
}

.dupont-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1d4ed8;
}

.report-pager {
  display: flex;
  align-items: center;
  gap: 4px;
}

.current-period {
  min-width: 100px;
  text-align: center;
  font-size: 13px;
  color: #333;
  padding: 0 8px;
}

.dupont-tree {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tree-canvas {
  transition: transform 0.2s;
  transform-origin: top center;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.node-root {
  display: flex;
  justify-content: center;
}

.node-card {
  display: inline-block;
  background: #fff;
  border: 1px solid #d0d0d0;
  border-radius: 4px;
  padding: 10px 16px;
  min-width: 120px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.node-card:hover {
  border-color: #1d4ed8;
  box-shadow: 0 2px 8px rgba(29, 78, 216, 0.15);
  transform: translateY(-1px);
}

.node-card-root {
  background: linear-gradient(135deg, #1d4ed8, #3b82f6);
  color: #fff;
  border-color: #1d4ed8;
  min-width: 160px;
}

.node-card-root .node-label,
.node-card-root .node-value,
.node-card-root .node-yoy {
  color: #fff;
}

.node-card-l1 {
  background: #f0f7ff;
  border-color: #91caff;
  min-width: 140px;
}

.node-card-l2 {
  background: #fff;
  border-color: #d9d9d9;
  min-width: 130px;
}

.node-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.node-value {
  font-size: 16px;
  font-weight: 600;
  color: #1d4ed8;
}

.node-card-l2 .node-value {
  color: #333;
}

.node-unit {
  font-size: 11px;
  font-weight: normal;
  margin-left: 2px;
  opacity: 0.7;
}

.node-yoy {
  font-size: 11px;
  margin-top: 4px;
}

.yoy-up { color: #cf1322; }
.node-card-root .yoy-up { color: #ffd591; }
.yoy-down { color: #52c41a; }
.node-card-root .yoy-down { color: #b7eb8f; }

.formula-line {
  text-align: center;
  color: #1d4ed8;
  font-size: 18px;
  font-weight: 600;
}

.level {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.level-1-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.op-symbol {
  font-size: 20px;
  font-weight: 700;
  color: #1d4ed8;
}

.connector {
  width: 2px;
  height: 16px;
  background: #d9d9d9;
  margin: 0 auto;
}

.level-2-item {
  display: flex;
}

.subtree-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  margin-top: 8px;
}

.node-detail-panel {
  margin-top: 24px;
  border-top: 1px dashed #d9d9d9;
  padding-top: 16px;
}

.detail-row {
  margin-bottom: 8px;
  font-size: 13px;
}

.detail-label {
  color: #666;
}

.detail-value {
  font-weight: 600;
  color: #1d4ed8;
  font-size: 16px;
}

.detail-chart {
  margin-top: 12px;
}

.chart-title {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 140px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.bar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 50px;
}

.bar-wrapper {
  width: 100%;
  height: 100px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.bar-fill {
  width: 70%;
  min-height: 4px;
  border-radius: 2px 2px 0 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 2px;
  color: #fff;
  font-size: 10px;
  transition: all 0.2s;
}

.bar-value {
  white-space: nowrap;
  text-shadow: 0 0 2px rgba(0,0,0,0.3);
}

.bar-label {
  font-size: 11px;
  color: #999;
  text-align: center;
}

.zoom-controls {
  position: absolute;
  right: 24px;
  bottom: 24px;
}
</style>
