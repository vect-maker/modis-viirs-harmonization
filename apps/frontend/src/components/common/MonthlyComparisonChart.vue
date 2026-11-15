<script lang="ts">
export interface ComparisonHistoric {
  count: number
  p25: number | null
  median: number | null
  p75: number | null
  max: number | null
}

export interface ComparisonMonth {
  month: number
  has_data: boolean
  year_count: number | null
  year_raw_count: number | null
  historic: ComparisonHistoric
  anomaly_pct_median: number | null
}

export type MonthStatus = 'above' | 'typical' | 'below' | 'no-data' | 'insufficient'

/** Con menos de 3 años de referencia los percentiles no describen un rango típico. */
export const MIN_BASELINE_YEARS = 3

export function monthStatus(month: ComparisonMonth): MonthStatus {
  const { p25, p75, count } = month.historic
  if (!month.has_data || month.year_count === null) return 'no-data'
  if (count < MIN_BASELINE_YEARS || p25 === null || p75 === null) return 'insufficient'
  if (month.year_count > p75) return 'above'
  if (month.year_count < p25) return 'below'
  return 'typical'
}

export const MONTH_LABELS = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
] as const

/** Mismos tonos que los tokens del tema: naranja/azul son distinguibles con daltonismo. */
export const STATUS_COLORS: Record<MonthStatus, string> = {
  above: '#e69f00',
  typical: '#64748b',
  below: '#38bdf8',
  insufficient: '#475569',
  'no-data': 'transparent',
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
  months: readonly ComparisonMonth[]
  year: number
  valueLabel: string
  fractionDigits: number
  description: string
}>()

const valueFormat = computed(
  () => new Intl.NumberFormat('en-US', { maximumFractionDigits: props.fractionDigits }),
)
const pctFormat = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0,
  signDisplay: 'exceptZero',
})

function formatValue(value: number | null): string {
  return value === null ? 'No data' : valueFormat.value.format(value)
}

function anomalyLabel(month: ComparisonMonth): string {
  if (month.anomaly_pct_median === null) return 'Above'
  return `${pctFormat.format(month.anomaly_pct_median)}%`
}

const STATUS_TEXT: Record<MonthStatus, string> = {
  above: 'Above the typical range',
  typical: 'Within the typical range',
  below: 'Below the typical range',
  insufficient: 'Not enough baseline years to compare',
  'no-data': 'Not in the archive yet',
}

function tooltipHtml(index: number): string {
  const month = props.months[index]
  if (!month) return ''
  const status = monthStatus(month)
  const { median, p25, p75, count } = month.historic
  const rows = [
    `<div style="font-weight:600">${MONTH_LABELS[index]} ${props.year}</div>`,
    `<div style="margin-top:2px;color:${status === 'no-data' ? '#94a3b8' : '#ffe066'}">${formatValue(month.year_count)} ${status === 'no-data' ? '' : props.valueLabel}</div>`,
  ]
  if (median !== null) {
    rows.push(
      `<div style="margin-top:6px;color:#cbd5e1">Median: ${formatValue(median)}</div>`,
      `<div style="color:#cbd5e1">Typical range: ${formatValue(p25)} to ${formatValue(p75)}</div>`,
      `<div style="color:#94a3b8">Baseline: ${count} ${count === 1 ? 'year' : 'years'}</div>`,
    )
  }
  rows.push(`<div style="margin-top:6px;color:#f3f4f6">${STATUS_TEXT[status]}</div>`)
  return rows.join('')
}

const chartOption = computed(() => {
  const baselineReady = (m: ComparisonMonth) =>
    m.historic.count >= MIN_BASELINE_YEARS && m.historic.p25 !== null && m.historic.p75 !== null

  const bandBase = props.months.map((m) => (baselineReady(m) ? m.historic.p25 : null))
  const bandSpan = props.months.map((m) =>
    baselineReady(m) ? (m.historic.p75 ?? 0) - (m.historic.p25 ?? 0) : null,
  )
  const median = props.months.map((m) => m.historic.median)

  const bars = props.months.map((m) => {
    const status = monthStatus(m)
    const flagged = status === 'above' || status === 'below'
    return {
      value: m.year_count,
      itemStyle: {
        color: STATUS_COLORS[status],
        borderRadius: [3, 3, 0, 0],
      },
      label: {
        show: flagged,
        position: 'top',
        distance: 4,
        color: status === 'above' ? '#ffe066' : '#7dd3fc',
        fontSize: 11,
        fontWeight: 600,
        formatter: () => anomalyLabel(m),
      },
    }
  })

  return {
    animationDuration: 200,
    grid: { top: 28, right: 12, bottom: 28, left: 52 },
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
      data: [...MONTH_LABELS],
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (value: number) =>
          new Intl.NumberFormat('en-US', { notation: 'compact' }).format(value),
      },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
    },
    series: [
      {
        name: 'Typical range floor',
        type: 'line',
        stack: 'band',
        data: bandBase,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        silent: true,
        z: 1,
      },
      {
        name: 'Typical range',
        type: 'line',
        stack: 'band',
        data: bandSpan,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(203, 213, 225, 0.11)' },
        silent: true,
        z: 1,
      },
      {
        name: String(props.year),
        type: 'bar',
        data: bars,
        barMaxWidth: 34,
        z: 2,
      },
      {
        name: 'Median',
        type: 'line',
        data: median,
        symbol: 'none',
        lineStyle: { color: '#cbd5e1', width: 1.5, type: [5, 4] },
        silent: true,
        z: 3,
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
