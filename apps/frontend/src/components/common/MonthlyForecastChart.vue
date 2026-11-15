<script lang="ts">
export interface ForecastTrainPoint {
  month: string
  actual: number
}

export interface ForecastTestPoint {
  month: string
  actual: number
  predicted: number
  lower_80: number
  upper_80: number
  lower_95: number
  upper_95: number
}

export interface ForecastFuturePoint {
  month: string
  predicted: number
  lower_80: number
  upper_80: number
  lower_95: number
  upper_95: number
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const props = defineProps<{
  train: readonly ForecastTrainPoint[]
  test: readonly ForecastTestPoint[]
  future: readonly ForecastFuturePoint[]
  description: string
}>()

const intFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

// Mostramos los últimos 36 meses de entrenamiento para que el tramo de validación y pronóstico se lea con claridad.
const visibleTrain = computed(() => props.train.slice(-36))

const timeline = computed(() => {
  const items: {
    month: string
    phase: 'train' | 'test' | 'future'
    actual: number | null
    predicted: number | null
    lower80: number | null
    upper80: number | null
    lower95: number | null
    upper95: number | null
  }[] = []

  for (const t of visibleTrain.value) {
    items.push({
      month: t.month,
      phase: 'train',
      actual: t.actual,
      predicted: null,
      lower80: null,
      upper80: null,
      lower95: null,
      upper95: null,
    })
  }
  for (const t of props.test) {
    items.push({
      month: t.month,
      phase: 'test',
      actual: t.actual,
      predicted: t.predicted,
      lower80: t.lower_80,
      upper80: t.upper_80,
      lower95: t.lower_95,
      upper95: t.upper_95,
    })
  }
  for (const f of props.future) {
    items.push({
      month: f.month,
      phase: 'future',
      actual: null,
      predicted: f.predicted,
      lower80: f.lower_80,
      upper80: f.upper_80,
      lower95: f.lower_95,
      upper95: f.upper_95,
    })
  }
  return items
})

function tooltipHtml(index: number): string {
  const row = timeline.value[index]
  if (!row) return ''
  const phaseLabel =
    row.phase === 'train'
      ? 'Training history'
      : row.phase === 'test'
        ? 'Validation holdout'
        : 'Future forecast'
  const lines = [
    `<div style="font-weight:600">${row.month} · <span style="color:#94a3b8;font-weight:400">${phaseLabel}</span></div>`,
  ]
  if (row.actual !== null) {
    lines.push(`<div style="margin-top:3px;color:#cbd5e1">Observed: ${intFmt.format(row.actual)}</div>`)
  }
  if (row.predicted !== null) {
    lines.push(
      `<div style="color:#ffe066">Predicted: ${intFmt.format(Math.round(row.predicted))}</div>`,
    )
  }
  if (row.lower80 !== null && row.upper80 !== null) {
    lines.push(
      `<div style="margin-top:3px;color:#38bdf8">80% CI: ${intFmt.format(Math.round(row.lower80))} – ${intFmt.format(Math.round(row.upper80))}</div>`,
    )
  }
  if (row.lower95 !== null && row.upper95 !== null) {
    lines.push(
      `<div style="color:#94a3b8">95% CI: ${intFmt.format(Math.round(row.lower95))} – ${intFmt.format(Math.round(row.upper95))}</div>`,
    )
  }
  return lines.join('')
}

const chartOption = computed(() => {
  const rows = timeline.value
  const months = rows.map((r) => r.month)
  const actuals = rows.map((r) => r.actual)
  const preds = rows.map((r) => r.predicted)
  const base95 = rows.map((r) => r.lower95)
  const span95 = rows.map((r) =>
    r.lower95 !== null && r.upper95 !== null ? Math.max(0, r.upper95 - r.lower95) : null,
  )
  const base80 = rows.map((r) => r.lower80)
  const span80 = rows.map((r) =>
    r.lower80 !== null && r.upper80 !== null ? Math.max(0, r.upper80 - r.lower80) : null,
  )

  return {
    animationDuration: 200,
    grid: { top: 28, right: 16, bottom: 28, left: 56 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: 'rgba(255,255,255,0.16)' } },
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
      data: months,
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
        name: '95% CI Floor',
        type: 'line',
        stack: 'ci95',
        data: base95,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        silent: true,
        z: 1,
      },
      {
        name: '95% CI',
        type: 'line',
        stack: 'ci95',
        data: span95,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(56, 189, 248, 0.10)' },
        silent: true,
        z: 1,
      },
      {
        name: '80% CI Floor',
        type: 'line',
        stack: 'ci80',
        data: base80,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        silent: true,
        z: 2,
      },
      {
        name: '80% CI',
        type: 'line',
        stack: 'ci80',
        data: span80,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(230, 159, 0, 0.20)' },
        silent: true,
        z: 2,
      },
      {
        name: 'Observed',
        type: 'line',
        data: actuals,
        symbol: 'circle',
        symbolSize: 4,
        itemStyle: { color: '#94a3b8' },
        lineStyle: { color: '#cbd5e1', width: 2 },
        z: 3,
      },
      {
        name: 'Predicted (Ridge)',
        type: 'line',
        data: preds,
        symbol: 'diamond',
        symbolSize: 6,
        itemStyle: { color: '#e69f00' },
        lineStyle: { color: '#e69f00', width: 2.2, type: 'dashed' },
        z: 4,
      },
    ],
  }
})
</script>

<template>
  <div role="img" :aria-label="description" class="h-[22rem] w-full">
    <VChart :option="chartOption" autoresize aria-hidden="true" />
  </div>
</template>
