<template>
  <div class="dupont-analysis">
    <div class="dupont-header">
      <h3 class="dupont-title">杜邦分析结构图</h3>
      <div class="report-pager">
        <a-button type="text" size="small" :disabled="!canPrev" @click="prevReport">
          <template #icon><left-outlined /></template>
        </a-button>
        <span class="current-period">{{ currentReportName || '请选择报告期' }}</span>
        <a-button type="text" size="small" :disabled="!canNext" @click="nextReport">
          <template #icon><right-outlined /></template>
        </a-button>
      </div>
    </div>

    <a-spin :spinning="loading">
      <div v-if="!loading && roeNode" class="dupont-container">
        <!-- 上方：树形结构 -->
        <div class="dupont-tree">
          <div class="tree-canvas">
            <!-- 顶层 ROE -->
            <div class="tree-node node-root" @click="onNodeClick('roe')">
              <div class="node-card node-card-root" :class="{ active: selectedKey === 'roe' }">
                <div class="node-label">ROE 净资产收益率</div>
                <div class="node-value">
                  {{ formatVal(roeNode.value) }}<span class="node-unit">{{ roeNode.unit }}</span>
                </div>
                <div v-if="roeNode.yoy != null" class="node-yoy" :class="roeNode.yoy >= 0 ? 'yoy-up' : 'yoy-down'">
                  同比 {{ roeNode.yoy >= 0 ? '+' : '' }}{{ roeNode.yoy }}%
                </div>
              </div>
            </div>

            <!-- 公式连接 -->
            <div v-if="expandedKeys.has('roe')" class="formula-line">＝</div>

            <!-- 一级驱动 -->
            <div v-if="expandedKeys.has('roe')" class="tree-level tree-level-1">
              <template v-for="(child, idx) in roeNode.children" :key="child.key">
                <span v-if="idx > 0" class="op-symbol">×</span>
                <div class="tree-node-with-sub">
                  <div class="tree-node" @click="onNodeClick(child.key)">
                    <div
                      class="node-card node-card-l1"
                      :class="{ active: selectedKey === child.key, expandable: child.children?.length }"
                    >
                      <div class="node-label">{{ child.name }}</div>
                      <div class="node-value">
                        {{ formatVal(child.value) }}<span class="node-unit">{{ child.unit }}</span>
                      </div>
                      <div v-if="child.yoy != null" class="node-yoy" :class="child.yoy >= 0 ? 'yoy-up' : 'yoy-down'">
                        同比 {{ child.yoy >= 0 ? '+' : '' }}{{ child.yoy }}%
                      </div>
                      <div v-if="child.children?.length" class="expand-hint">
                        {{ expandedKeys.has(child.key) ? '▼ 已展开' : '▶ 可展开' }}
                      </div>
                    </div>
                  </div>
                  <!-- 二级驱动：在对应父节点下方展开 -->
                  <div v-if="expandedKeys.has(child.key) && child.children?.length" class="subtree-wrapper">
                    <div class="connector"></div>
                    <div class="tree-level tree-level-2">
                      <div
                        v-for="sub in child.children"
                        :key="sub.key"
                        class="tree-node"
                        @click="onNodeClick(sub.key)"
                      >
                        <div
                          class="node-card node-card-l2"
                          :class="{ active: selectedKey === sub.key }"
                        >
                          <div class="node-label">{{ sub.name }}</div>
                          <div class="node-value">
                            {{ formatVal(sub.value) }}<span class="node-unit">{{ sub.unit }}</span>
                          </div>
                          <div v-if="sub.yoy != null" class="node-yoy" :class="sub.yoy >= 0 ? 'yoy-up' : 'yoy-down'">
                            同比 {{ sub.yoy >= 0 ? '+' : '' }}{{ sub.yoy }}%
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <!-- 资产质量分组 -->
            <template v-if="assetQualityNode && assetQualityNode.children?.length">
              <div v-if="expandedKeys.has('asset_quality')" class="formula-line">＋</div>
              <div class="tree-node" @click="onNodeClick('asset_quality')">
                <div
                  class="node-card node-card-asset"
                  :class="{ active: selectedKey === 'asset_quality' }"
                >
                  <div class="node-label">资产质量</div>
                  <div class="node-value node-value-small">辅助分析</div>
                  <div v-if="expandedKeys.has('asset_quality')" class="expand-hint">▼ 已展开</div>
                  <div v-else class="expand-hint">▶ 可展开</div>
                </div>
              </div>
              <div v-if="expandedKeys.has('asset_quality')" class="subtree-wrapper">
                <div class="connector"></div>
                <div class="tree-level tree-level-2">
                  <div
                    v-for="sub in assetQualityNode.children"
                    :key="sub.key"
                    class="tree-node"
                    @click="onNodeClick(sub.key)"
                  >
                    <div
                      class="node-card node-card-l2"
                      :class="{ active: selectedKey === sub.key }"
                    >
                      <div class="node-label">{{ sub.name }}</div>
                      <div class="node-value">
                        {{ formatVal(sub.value) }}<span class="node-unit">{{ sub.unit }}</span>
                      </div>
                      <div v-if="sub.yoy != null" class="node-yoy" :class="sub.yoy >= 0 ? 'yoy-up' : 'yoy-down'">
                        同比 {{ sub.yoy >= 0 ? '+' : '' }}{{ sub.yoy }}%
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- 下方：选中节点详情 + 6期柱状图 -->
        <div v-if="selectedNode" class="detail-panel">
          <a-card size="small" :bordered="false">
            <div class="detail-header">
              <div class="detail-title-wrap">
                <span class="detail-title">{{ selectedNode.name }}</span>
                <a-tag color="blue">{{ selectedNode.formula }}</a-tag>
              </div>
              <div class="detail-stats">
                <div class="stat-item">
                  <div class="stat-label">当前值</div>
                  <div class="stat-value">
                    {{ formatVal(selectedNode.value) }} <span class="stat-unit">{{ selectedNode.unit }}</span>
                  </div>
                </div>
                <div class="stat-item" v-if="selectedNode.yoy != null">
                  <div class="stat-label">同比变化</div>
                  <div class="stat-value" :class="selectedNode.yoy >= 0 ? 'yoy-up' : 'yoy-down'">
                    {{ selectedNode.yoy >= 0 ? '+' : '' }}{{ selectedNode.yoy }}%
                  </div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">报告期</div>
                  <div class="stat-value-small">{{ currentReportName }}</div>
                </div>
              </div>
            </div>

            <!-- 6期柱状图 -->
            <div class="chart-section">
              <div class="chart-title">近6期数据趋势</div>
              <div class="bar-chart">
                <div
                  v-for="(bar, i) in barData"
                  :key="i"
                  class="bar-item"
                >
                  <div class="bar-wrapper">
                    <div
                      class="bar-fill"
                      :style="{
                        height: bar.height + '%',
                        background: bar.color,
                      }"
                    >
                      <span class="bar-value">{{ bar.valueLabel }}</span>
                    </div>
                  </div>
                  <div class="bar-label">{{ bar.label }}</div>
                </div>
              </div>
            </div>
          </a-card>
        </div>
      </div>
      <a-empty v-else-if="!loading" description="暂无数据，请先采集该股票数据" />
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { LeftOutlined, RightOutlined } from '@ant-design/icons-vue'
import { financeApi, type DupontNode } from '@/api/finance'

const props = defineProps<{
  stockCode: string
}>()

const loading = ref(false)
const rawNodes = ref<DupontNode[]>([])
const reportDates = ref<string[]>([])
const reportNames = ref<string[]>([])
const currentReportIdx = ref(0)
const expandedKeys = ref<Set<string>>(new Set())
const selectedKey = ref<string>('roe')
const zoom = ref(1)

function round2(v: number): number {
  return Math.round(v * 100) / 100
}

/**
 * 根据 currentReportIdx 提取该报告期对应的节点值。
 * nodes 顺序与 reportDates 倒序一致：nodes[0] = 最新一期。
 * 节点内部的 history 顺序与 nodes 顺序一致（最新在前），需要再做一次倒序映射。
 */
function getDisplayNodes(): DupontNode[] {
  if (!rawNodes.value.length) return []
  const idx = currentReportIdx.value
  return rawNodes.value.map((node) => cloneNodeAt(node, idx))
}

function cloneNodeAt(node: DupontNode, idx: number): DupontNode {
  // 后端 history 是按报告期正序（早→晚），reportDates 是倒序（晚→早）
  // 所以 reportDates[i] 对应 history[total-1-i]
  const hist = node.history || []
  const n = hist.length
  const srcIdx = n - 1 - idx
  const currentVal = srcIdx >= 0 && srcIdx < n ? hist[srcIdx] : null
  let yoy: number | null = null
  if (srcIdx >= 1 && hist[srcIdx - 1] != null && hist[srcIdx - 1] !== 0 && hist[srcIdx] != null) {
    yoy = round2((hist[srcIdx] - hist[srcIdx - 1]) / Math.abs(hist[srcIdx - 1]) * 100)
  }
  return {
    ...node,
    value: currentVal,
    yoy,
    children: (node.children || []).map((c) => cloneNodeAt(c, idx)),
  }
}

const displayNodes = computed(() => getDisplayNodes())
const roeNode = computed(() => displayNodes.value[0])
const assetQualityNode = computed(() => displayNodes.value[1])

const currentReportName = computed(() => {
  if (!reportNames.value.length) return ''
  return reportNames.value[currentReportIdx.value] || ''
})

const canPrev = computed(() => currentReportIdx.value < reportDates.value.length - 1)
const canNext = computed(() => currentReportIdx.value > 0)

function prevReport() {
  if (canPrev.value) currentReportIdx.value++
}
function nextReport() {
  if (canNext.value) currentReportIdx.value--
}

/** 点击节点：选中 + 若有子节点则展开 */
function onNodeClick(key: string) {
  selectedKey.value = key
  if (key === 'roe') {
    expandedKeys.value = new Set(['roe'])
    return
  }
  const node = findNode(displayNodes.value, key)
  if (node && node.children && node.children.length) {
    const next = new Set(expandedKeys.value)
    if (next.has(key)) {
      next.delete(key)
    } else {
      next.add(key)
    }
    expandedKeys.value = next
  }
}

function findNode(list: DupontNode[], key: string): DupontNode | null {
  for (const n of list) {
    if (n.key === key) return n
    const sub = findNode(n.children || [], key)
    if (sub) return sub
  }
  return null
}

const selectedNode = computed(() => {
  if (!displayNodes.value.length) return null
  if (selectedKey.value === 'asset_quality') return assetQualityNode.value
  return findNode(displayNodes.value, selectedKey.value) || roeNode.value
})

/** 柱状图数据：取最近6期，从旧到新展示 */
const barData = computed(() => {
  if (!selectedNode.value) return []
  const node = selectedNode.value
  const hist = node.history || []
  const n = hist.length
  // 截取最近6期：history 是正序（早→晚），截取后6个
  const recent = hist.slice(Math.max(0, n - 6))
  const recentDates = reportDates.value.slice(Math.max(0, n - 6)).reverse() // 转正序对应
  const recentNames = reportNames.value.slice(Math.max(0, n - 6)).reverse()

  const nums = recent.filter((x): x is number => x != null && !isNaN(x))
  if (!nums.length) {
    return recent.map((v, i) => ({
      value: v,
      valueLabel: v != null ? formatVal(v) : '-',
      label: (recentNames[i] || recentDates[i] || '').replace(/报告|报/g, ''),
      height: 0,
      color: '#d9d9d9',
    }))
  }
  const max = Math.max(...nums.map(Math.abs))
  const min = Math.min(...nums)
  const range = max - min || 1

  return recent.map((v, i) => {
    let height = 0
    let color = '#1d4ed8'
    if (v == null) {
      height = 0
      color = '#d9d9d9'
    } else if (Math.abs(max) < 100) {
      // 比例类（如净利率）用相对值
      height = (Math.abs(v) / Math.max(max, 0.001)) * 100
    } else {
      // 绝对值类
      height = ((v - Math.min(0, min)) / range) * 100
    }
    if (v != null && v < 0) color = '#ff4d4f'
    return {
      value: v,
      valueLabel: v != null ? formatVal(v) : '-',
      label: (recentNames[i] || recentDates[i] || '').replace(/报告|报/g, ''),
      height: Math.min(100, Math.max(2, height)),
      color,
    }
  })
})

function formatVal(v: number | null | undefined): string {
  if (v == null) return '-'
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(2)
}

async function loadData() {
  if (!props.stockCode) return
  loading.value = true
  try {
    const res = await financeApi.getDupont(props.stockCode, 8)
    if (res.code === 0 && res.data) {
      rawNodes.value = res.data.nodes || []
      reportDates.value = res.data.report_dates || []
      reportNames.value = res.data.report_names || []
      // 默认选中 ROE 并展开
      selectedKey.value = 'roe'
      expandedKeys.value = new Set(['roe'])
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
  min-width: 120px;
  text-align: center;
  font-size: 13px;
  color: #333;
  padding: 0 8px;
}

.dupont-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dupont-tree {
  min-height: 300px;
}

.dupont-tree {
  position: relative;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 24px 12px;
  background: linear-gradient(180deg, #f0f7ff 0%, #fafcff 100%);
  overflow-x: auto;
}

.tree-canvas {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.tree-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.node-card {
  display: inline-block;
  background: #fff;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  padding: 10px 16px;
  min-width: 130px;
  text-align: center;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.node-card:hover {
  border-color: #2563eb;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
  transform: translateY(-1px);
}

.node-card.active {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.node-card-root {
  background: #fff !important;
  border: 2px solid #3b82f6 !important;
  color: #1e3a8a !important;
  min-width: 180px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}
.node-card-root .node-label {
  color: #1e40af !important;
  font-weight: 600;
  font-size: 14px;
}
.node-card-root .node-value {
  color: #dc2626 !important;
  font-weight: 700;
  font-size: 22px;
}
.node-card-root .node-unit {
  color: #6b7280 !important;
  font-size: 13px;
  font-weight: 400;
}
.node-card-root .node-yoy {
  color: #6b7280 !important;
  font-size: 12px;
}
.node-card-root .node-yoy.yoy-up {
  color: #dc2626 !important;
}
.node-card-root .node-yoy.yoy-down {
  color: #16a34a !important;
}
.node-card-root .expand-hint {
  color: #6b7280 !important;
}

.node-card-l1 {
  background: #fff;
  border: 2px solid #93c5fd;
  min-width: 150px;
}
.node-card-l1 .node-label { color: #1e40af; }
.node-card-l1 .node-value { color: #2563eb; }

.node-card-l2 {
  background: #fff;
  border: 1px solid #e5e7eb;
  min-width: 130px;
}
.node-card-l2 .node-label { color: #6b7280; }
.node-card-l2 .node-value { color: #374151; }

.node-card-asset {
  background: #fffbeb;
  border: 2px solid #fcd34d;
  min-width: 130px;
}
.node-card-asset .node-label { color: #92400e; }
.node-card-asset .node-value { color: #d97706; }

.node-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}
.node-card-root .node-label { color: rgba(255,255,255,0.85); }

.node-value {
  font-size: 16px;
  font-weight: 600;
  color: #1d4ed8;
}
.node-card-l2 .node-value { color: #333; }
.node-card-asset .node-value { color: #d46b08; }

.node-value-small {
  font-size: 12px;
  font-weight: normal;
  color: #d46b08;
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

.expand-hint {
  font-size: 10px;
  margin-top: 4px;
  color: #999;
  opacity: 0.8;
}
.node-card-root .expand-hint { color: rgba(255,255,255,0.7); }

.formula-line {
  color: #1d4ed8;
  font-size: 18px;
  font-weight: 600;
  text-align: center;
}

.tree-node-with-sub {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tree-level {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.op-symbol {
  font-size: 20px;
  font-weight: 700;
  color: #1d4ed8;
}

.connector {
  width: 2px;
  height: 14px;
  background: #d9d9d9;
  margin: 0 auto;
}

.subtree-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

/* 下方详情 */
.detail-panel {
  width: 100%;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.detail-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d4ed8;
}

.detail-stats {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.detail-stats .stat-item {
  flex: 1;
  min-width: 100px;
}

.stat-item {
  background: #f8fafc;
  padding: 10px 12px;
  border-radius: 4px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #1d4ed8;
}

.stat-value-small {
  font-size: 13px;
  color: #333;
  font-weight: 500;
}

.stat-unit {
  font-size: 11px;
  opacity: 0.7;
  margin-left: 2px;
}

.chart-section {
  margin-top: 8px;
}

.chart-title {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
  font-weight: 500;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 6px;
  height: 180px;
  padding: 8px 4px 4px;
  border-bottom: 1px solid #e5e7eb;
  background: #fafafa;
  border-radius: 6px;
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
  height: 140px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  position: relative;
}

.bar-fill {
  width: 70%;
  min-height: 4px;
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
  position: relative;
}

.bar-value {
  position: absolute;
  top: -18px;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  font-size: 10px;
  font-weight: 600;
  color: #374151;
  background: rgba(255,255,255,0.9);
  padding: 1px 4px;
  border-radius: 3px;
}

.bar-label {
  font-size: 11px;
  color: #999;
  text-align: center;
  white-space: nowrap;
}
</style>
