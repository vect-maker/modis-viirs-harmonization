<script lang="ts">
export interface SpatialAnomalyPoint {
  id: string
  latitude: number
  longitude: number
  frp: number | null
  acq_datetime: string
  anomaly: number
  is_anomaly: boolean
  score: number
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([CanvasRenderer, ScatterChart, GridComponent, TooltipComponent])

const props = defineProps<{
  points: readonly SpatialAnomalyPoint[]
  mode: 'geo' | 'score'
  description: string
}>()

const frpFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

const chartOption = computed(() => {
  const normals: { value: number[]; pt: SpatialAnomalyPoint }[] = []
  const anomalies: { value: number[]; pt: SpatialAnomalyPoint }[] = []

  for (const pt of props.points) {
    const coords =
      props.mode === 'geo'
        ? [pt.longitude, pt.latitude]
        : [pt.score, pt.frp ?? 0]
    if (pt.is_anomaly) {
      anomalies.push({ value: coords, pt })
    } else {
      normals.push({ value: coords, pt })
    }
  }

  return {
    animationDuration: 200,
    grid: { top: 24, right: 20, bottom: 36, left: 56 },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#11161d',
      borderColor: '#28323e',
      borderWidth: 1,
      textStyle: { color: '#f3f4f6', fontSize: 12 },
      formatter(param: unknown) {
        const p = param as { data?: { pt?: SpatialAnomalyPoint } }
        const pt = p.data?.pt
        if (!pt) return ''
        return [
          `<div style="font-weight:600;color:${pt.is_anomaly ? '#ffe066' : '#cbd5e1'}">${pt.is_anomaly ? 'Spatial Anomaly (Outlier)' : 'Normal Cluster Point'}</div>`,
          `<div style="margin-top:2px;color:#f3f4f6">${pt.latitude.toFixed(4)}°N, ${pt.longitude.toFixed(4)}°E</div>`,
          `<div style="color:#cbd5e1">Decision score: ${pt.score.toFixed(4)}</div>`,
          `<div style="color:#cbd5e1">FRP: ${pt.frp !== null ? `${frpFmt.format(pt.frp)} MW` : '—'}</div>`,
          `<div style="color:#94a3b8">${pt.acq_datetime.slice(0, 19)} UTC</div>`,
        ].join('')
      },
    },
    xAxis: {
      type: 'value',
      scale: true,
      name: props.mode === 'geo' ? 'Longitude (°)' : 'IsolationForest Decision Score',
      nameLocation: 'middle',
      nameGap: 24,
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (v: number) => (props.mode === 'geo' ? `${v.toFixed(1)}°` : v.toFixed(2)),
      },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
    },
    yAxis: {
      type: 'value',
      scale: true,
      name: props.mode === 'geo' ? 'Latitude (°)' : 'FRP (MW)',
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (v: number) => (props.mode === 'geo' ? `${v.toFixed(1)}°` : `${frpFmt.format(v)}`),
      },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
    },
    series: [
      {
        name: 'Normal points',
        type: 'scatter',
        data: normals,
        symbolSize: 5,
        itemStyle: { color: '#64748b', opacity: 0.45 },
        z: 1,
      },
      {
        name: 'Spatial anomalies',
        type: 'scatter',
        data: anomalies,
        symbol: 'diamond',
        symbolSize: 9,
        itemStyle: {
          color: '#e69f00',
          borderColor: '#ffe066',
          borderWidth: 1,
          opacity: 0.95,
        },
        z: 3,
      },
    ],
  }
})
</script>

<template>
  <div role="img" :aria-label="description" class="h-[32rem] w-full sm:h-[38rem] lg:h-[42rem]">
    <VChart :option="chartOption" autoresize aria-hidden="true" />
  </div>
</template>
