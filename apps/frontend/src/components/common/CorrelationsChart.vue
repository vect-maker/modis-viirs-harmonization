<script lang="ts">
export interface CorrelationPair {
  x: string
  y: string
  n: number
  pearson_r: number | null
  r2: number | null
  mean_x: number | null
  std_x?: number | null
  mean_y: number | null
  std_y?: number | null
}

export const CORR_VARS = ['frp', 'confidence', 'bright_tir', 'bright_mir'] as const
export const CORR_LABELS: Record<string, string> = {
  frp: 'FRP (MW)',
  confidence: 'Confidence (%)',
  bright_tir: 'TIR (K)',
  bright_mir: 'MIR (K)',
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([CanvasRenderer, HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent])

const props = defineProps<{
  pairs: readonly CorrelationPair[]
  statMode: 'pearson_r' | 'r2'
  description: string
}>()

const intFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

const pairLookup = computed(() => {
  const map = new Map<string, CorrelationPair>()
  for (const p of props.pairs) {
    map.set(`${p.x}:${p.y}`, p)
    map.set(`${p.y}:${p.x}`, {
      x: p.y,
      y: p.x,
      n: p.n,
      pearson_r: p.pearson_r,
      r2: p.r2,
      mean_x: p.mean_y,
      std_x: p.std_y,
      mean_y: p.mean_x,
      std_y: p.std_x,
    })
  }
  return map
})

const chartOption = computed(() => {
  const labels = CORR_VARS.map((k) => CORR_LABELS[k] ?? k)
  const cells: { value: [number, number, number]; pair?: CorrelationPair }[] = []

  CORR_VARS.forEach((vx, i) => {
    CORR_VARS.forEach((vy, j) => {
      if (i === j) {
        cells.push({ value: [i, j, 1] })
      } else {
        const pair = pairLookup.value.get(`${vx}:${vy}`)
        const raw =
          props.statMode === 'pearson_r' ? (pair?.pearson_r ?? 0) : (pair?.r2 ?? 0)
        cells.push({ value: [i, j, Number(raw.toFixed(3))], pair })
      }
    })
  })

  return {
    animationDuration: 200,
    grid: { top: 20, right: 86, bottom: 36, left: 108 },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#11161d',
      borderColor: '#28323e',
      borderWidth: 1,
      textStyle: { color: '#f3f4f6', fontSize: 12 },
      formatter(param: unknown) {
        const p = param as { data?: { value?: [number, number, number]; pair?: CorrelationPair } }
        const val = p.data?.value
        if (!val) return ''
        const [i, j] = val
        const lx = labels[i] ?? ''
        const ly = labels[j] ?? ''
        const pair = p.data?.pair
        if (!pair) {
          return `<div style="font-weight:600">${lx} vs. ${ly}</div><div style="color:#ffe066">Identity: 1.000</div>`
        }
        return [
          `<div style="font-weight:600">${lx} × ${ly}</div>`,
          `<div style="margin-top:3px;color:#ffe066">Pearson r: ${pair.pearson_r?.toFixed(4) ?? '—'} · R²: ${pair.r2?.toFixed(4) ?? '—'}</div>`,
          `<div style="color:#cbd5e1">Mean ${lx}: ${pair.mean_x?.toFixed(2) ?? '—'}</div>`,
          `<div style="color:#cbd5e1">Mean ${ly}: ${pair.mean_y?.toFixed(2) ?? '—'}</div>`,
          `<div style="margin-top:3px;color:#94a3b8">Sample size (n): ${intFmt.format(pair.n)}</div>`,
        ].join('')
      },
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisTick: { show: false },
      axisLabel: { color: '#cbd5e1', fontSize: 11 },
      splitArea: { show: false },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisTick: { show: false },
      axisLabel: { color: '#cbd5e1', fontSize: 11 },
      splitArea: { show: false },
    },
    visualMap: {
      min: props.statMode === 'pearson_r' ? -1 : 0,
      max: 1,
      calculable: false,
      orient: 'vertical',
      right: 12,
      top: 'middle',
      itemWidth: 12,
      itemHeight: 130,
      text: ['1.0', props.statMode === 'pearson_r' ? '-1.0' : '0.0'],
      textStyle: { color: '#94a3b8', fontSize: 10 },
      inRange: {
        color:
          props.statMode === 'pearson_r'
            ? ['#38bdf8', '#1f2730', '#b84a39', '#e69f00', '#ffe066']
            : ['#1f2730', '#2d1e3e', '#6b2d5c', '#b84a39', '#e69f00', '#ffe066'],
      },
    },
    series: [
      {
        name: 'Correlation matrix',
        type: 'heatmap',
        data: cells,
        itemStyle: {
          borderColor: '#181e24',
          borderWidth: 3,
          borderRadius: 4,
        },
        label: {
          show: true,
          color: '#f3f4f6',
          fontSize: 12,
          fontWeight: 600,
          formatter(param: unknown) {
            const p = param as { data?: { value?: [number, number, number] } }
            const v = p.data?.value?.[2]
            return v !== undefined ? v.toFixed(3) : ''
          },
        },
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
