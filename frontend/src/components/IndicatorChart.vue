<template>
  <div class="indicator-chart" ref="chartRef"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { FinIndicator } from '@/types'

const props = defineProps<{
  indicators: FinIndicator[]
  stockName?: string
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)

  const dates = [...new Set(props.indicators.map(i => i.report_date))].sort()

  const seriesData = [
    { name: 'ROE', key: 'roe' },
    { name: 'ROA', key: 'roa' },
    { name: '净利率', key: 'net_margin' },
    { name: '资产负债率', key: 'debt_to_assets' }
  ]

  const series = seriesData.map(s => ({
    name: s.name,
    type: 'line',
    data: dates.map(date => {
      const item = props.indicators.find(i => i.report_date === date)
      const value = item?.[s.key as keyof FinIndicator]
      return value !== null && value !== undefined ? parseFloat(value as string) : null
    }),
    smooth: true,
    connectNulls: true
  }))

  const option: echarts.EChartsOption = {
    title: {
      text: props.stockName ? `${props.stockName} 财务指标趋势` : '财务指标趋势',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 500
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        let result = `${params[0].axisValue}<br/>`
        params.forEach((param: any) => {
          const value = param.value !== null ? param.value.toFixed(2) + '%' : '-'
          result += `${param.marker} ${param.seriesName}: ${value}<br/>`
        })
        return result
      }
    },
    legend: {
      bottom: 10,
      data: seriesData.map(s => s.name)
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: series as any
  }

  chartInstance.setOption(option)
}

const handleResize = () => {
  chartInstance?.resize()
}

watch(() => props.indicators, () => {
  nextTick(() => {
    initChart()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    initChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.indicator-chart {
  width: 100%;
  height: 400px;
}
</style>
