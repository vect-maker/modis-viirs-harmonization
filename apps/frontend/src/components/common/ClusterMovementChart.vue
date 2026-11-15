<script lang="ts">
export interface MovementStepItem {
  fire_id: number
  timestamp: string
  centroid_lat: number
  centroid_lon: number
  direction_deg: number | null
  cardinal_direction: string | null
  distance_km: number
  apparent_speed_kmh: number
  hotspot_count: number
  total_frp: number
  angle_change_deg: number | null
  direction_changed: boolean
  empty_intervals_before: number
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent])

const props = defineProps<{
  steps: readonly MovementStepItem[]
  fireId: number
  description: string
}>()

const decFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })
const frpFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

function tooltipHtml(index: number): string {
  const step = props.steps[index]
  if (!step) return ''
  const dirText =
    step.direction_deg !== null
      ? `${step.cardinal_direction ?? ''} (${step.direction_deg.toFixed(1)}°)`
      : 'Initial centroid'
  return [
    `<div style="font-weight:600">Fire #${props.fireId} · Step ${index + 1}</div>`,
    `<div style="color:#94a3b8">${step.timestamp.slice(0, 19).replace('T', ' ')} UTC</div>`,
    `<div style="margin-top:4px;color:#ffe066">Apparent speed: ${decFmt.format(step.apparent_speed_kmh)} km/h (${decFmt.format(step.distance_km)} km)</div>`,
    `<div style="color:#38bdf8">Bearing: ${dirText}${step.direction_changed ? ' · Direction shift' : ''}</div>`,
    `<div style="color:#cbd5e1">Hotspots: ${step.hotspot_count} · Total FRP: ${frpFmt.format(step.total_frp)} MW</div>`,
    `<div style="color:#94a3b8">Centroid: ${step.centroid_lat.toFixed(4)}°N, ${step.centroid_lon.toFixed(4)}°E</div>`,
  ].join('')
}

const chartOption = computed(() => {
  const labels = props.steps.map((s) => s.timestamp.slice(5, 16).replace('T', ' '))
  const speeds = props.steps.map((s) => Number(s.apparent_speed_kmh.toFixed(3)))
  const distances = props.steps.map((s) => Number(s.distance_km.toFixed(3)))
  const frps = props.steps.map((s) => Number(s.total_frp.toFixed(1)))

  return {
    animationDuration: 200,
    grid: { top: 32, right: 56, bottom: 28, left: 54 },
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
      data: labels,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
    },
    yAxis: [
      {
        type: 'value',
        name: 'km / km/h',
        nameTextStyle: { color: '#94a3b8', fontSize: 10 },
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
      },
      {
        type: 'value',
        name: 'Total FRP (MW)',
        nameTextStyle: { color: '#ffe066', fontSize: 10 },
        axisLabel: { color: '#ffe066', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'Step distance (km)',
        type: 'bar',
        barMaxWidth: 24,
        itemStyle: { color: 'rgba(56, 189, 248, 0.55)', borderRadius: [3, 3, 0, 0] },
        data: distances,
      },
      {
        name: 'Apparent speed (km/h)',
        type: 'line',
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#e69f00' },
        lineStyle: { color: '#e69f00', width: 2.2 },
        data: speeds,
      },
      {
        name: 'Total FRP (MW)',
        type: 'line',
        yAxisIndex: 1,
        symbol: 'diamond',
        symbolSize: 5,
        itemStyle: { color: '#ffe066' },
        lineStyle: { color: '#ffe066', width: 1.6, type: 'dashed' },
        data: frps,
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
