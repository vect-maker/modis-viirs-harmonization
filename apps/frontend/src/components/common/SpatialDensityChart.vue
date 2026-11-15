<script lang="ts">
export interface SpatialDensityCell {
  cell_lat: number
  cell_lon: number
  count: number
  sum_frp: number
  avg_frp: number | null
  max_frp: number | null
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([CanvasRenderer, ScatterChart, GridComponent, TooltipComponent, VisualMapComponent])

const props = defineProps<{
  cells: readonly SpatialDensityCell[]
  cellSizeDeg: number
  description: string
}>()

const intFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const frpFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

const chartOption = computed(() => {
  const maxCount = Math.max(1, ...props.cells.map((c) => c.count))
  const logMax = Math.log10(maxCount + 1)

  const points = props.cells.map((c, idx) => ({
    value: [c.cell_lon, c.cell_lat, c.count, idx],
  }))

  return {
    animationDuration: 200,
    grid: { top: 24, right: 80, bottom: 36, left: 56 },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#11161d',
      borderColor: '#28323e',
      borderWidth: 1,
      textStyle: { color: '#f3f4f6', fontSize: 12 },
      formatter(param: unknown) {
        const p = param as { data?: { value?: number[] } }
        const idx = p.data?.value?.[3]
        const cell = idx !== undefined ? props.cells[idx] : undefined
        if (!cell) return ''
        return [
          `<div style="font-weight:600">${cell.cell_lat.toFixed(2)}°N, ${cell.cell_lon.toFixed(2)}°E</div>`,
          `<div style="margin-top:2px;color:#ffe066">${intFmt.format(cell.count)} detections</div>`,
          `<div style="color:#cbd5e1">Avg FRP: ${cell.avg_frp !== null ? `${frpFmt.format(cell.avg_frp)} MW` : '—'}</div>`,
          `<div style="color:#cbd5e1">Peak FRP: ${cell.max_frp !== null ? `${frpFmt.format(cell.max_frp)} MW` : '—'}</div>`,
          `<div style="color:#94a3b8">Cell size: ${props.cellSizeDeg}°</div>`,
        ].join('')
      },
    },
    visualMap: {
      min: 1,
      max: maxCount,
      dimension: 2,
      orient: 'vertical',
      right: 8,
      top: 'middle',
      itemWidth: 12,
      itemHeight: 220,
      text: ['High', 'Low'],
      textStyle: { color: '#94a3b8', fontSize: 10 },
      inRange: {
        color: ['#2d1e3e', '#6b2d5c', '#b84a39', '#e69f00', '#ffe066'],
      },
    },
    xAxis: {
      type: 'value',
      scale: true,
      name: 'Longitude (°)',
      nameLocation: 'middle',
      nameGap: 24,
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, formatter: (v: number) => `${v.toFixed(1)}°` },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
    },
    yAxis: {
      type: 'value',
      scale: true,
      name: 'Latitude (°)',
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, formatter: (v: number) => `${v.toFixed(1)}°` },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
    },
    series: [
      {
        name: 'Grid cell density',
        type: 'scatter',
        data: points,
        symbol: 'rect',
        symbolSize(val: number[]) {
          const count = val[2] ?? 1
          const ratio = logMax > 0 ? Math.log10(count + 1) / logMax : 0.5
          return Math.round(5 + ratio * 11)
        },
        itemStyle: {
          opacity: 0.88,
        },
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
