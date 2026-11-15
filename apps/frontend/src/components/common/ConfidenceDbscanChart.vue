<script lang="ts">
export interface ConfidenceDbscanPoint {
  confidence: number
  count: number
  cluster: number
  is_anomaly: boolean
}

const CLUSTER_PALETTE = ['#38bdf8', '#94a3b8', '#e69f00', '#a78bfa', '#34d399'] as const
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps<{
  points: readonly ConfidenceDbscanPoint[]
  description: string
}>()

const intFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

function clusterColor(pt: ConfidenceDbscanPoint): string {
  if (pt.is_anomaly || pt.cluster < 0) return '#b84a39'
  return CLUSTER_PALETTE[pt.cluster % CLUSTER_PALETTE.length] ?? '#38bdf8'
}

function tooltipHtml(index: number): string {
  const pt = props.points[index]
  if (!pt) return ''
  return [
    `<div style="font-weight:600">Confidence: ${pt.confidence}%</div>`,
    `<div style="margin-top:2px;color:#ffe066">${intFmt.format(pt.count)} detections</div>`,
    `<div style="margin-top:4px;color:${pt.is_anomaly ? '#f87171' : '#38bdf8'}">${pt.is_anomaly ? 'DBSCAN Noise / Anomaly (-1)' : `Cluster #${pt.cluster}`}</div>`,
  ].join('')
}

const chartOption = computed(() => {
  const categories = props.points.map((p) => `${p.confidence}%`)
  const bars = props.points.map((p) => ({
    value: p.count,
    itemStyle: {
      color: clusterColor(p),
      borderRadius: [3, 3, 0, 0],
      ...(p.is_anomaly ? { borderColor: '#ffe066', borderWidth: 1 } : {}),
    },
  }))

  return {
    animationDuration: 200,
    grid: { top: 24, right: 16, bottom: 28, left: 56 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(255, 255, 255, 0.04)' } },
      backgroundColor: '#11161d',
      borderColor: '#28323e',
      borderWidth: 1,
      textStyle: { color: '#f3f4f6', fontSize: 12 },
      formatter(params: unknown) {
        const list = Array.isArray(params) ? params : [params]
        const first = list[0] as { dataIndex?: number } | undefined
        return first?.dataIndex !== undefined ? tooltipHtml(first.dataIndex) : ''
      },
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (v: number) =>
          new Intl.NumberFormat('en-US', { notation: 'compact' }).format(v),
      },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
    },
    series: [
      {
        name: 'Detections by confidence',
        type: 'bar',
        barMaxWidth: 20,
        data: bars,
      },
    ],
  }
})
</script>

<template>
  <div role="img" :aria-label="description" class="h-[20rem] w-full">
    <VChart :option="chartOption" autoresize aria-hidden="true" />
  </div>
</template>
