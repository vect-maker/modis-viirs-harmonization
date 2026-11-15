<script lang="ts">
export type AnnualMetric = 'raw' | 'harmonized'

export interface AnnualRow {
  year: number
  months_in_archive: number
  complete: boolean
  total_hotspots: number
  modis_count: number
  viirs_count: number
  harmonized_index: number
}

export function annualValue(row: AnnualRow, metric: AnnualMetric): number {
  return metric === 'harmonized' ? row.harmonized_index : row.total_hotspots
}

/** Mediana de los años completos: los años parciales no son comparables. */
export function completeYearMedian(rows: readonly AnnualRow[], metric: AnnualMetric) {
  const values = rows
    .filter((row) => row.complete)
    .map((row) => annualValue(row, metric))
    .sort((a, b) => a - b)
  if (values.length === 0) return null
  const mid = Math.floor(values.length / 2)
  return values.length % 2 === 1
    ? (values[mid] ?? null)
    : ((values[mid - 1] ?? 0) + (values[mid] ?? 0)) / 2
}

/** Gris claro y naranja: difieren en luminosidad, legibles con daltonismo. */
export const SERIES_COLORS = {
  modis: '#94a3b8',
  viirs: '#e69f00',
  harmonized: '#e69f00',
} as const

export const VIIRS_FIRST_YEAR = 2012
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, GridComponent, MarkLineComponent, TooltipComponent])

const props = defineProps<{
  rows: readonly AnnualRow[]
  metric: AnnualMetric
  description: string
}>()

const PARTIAL_OPACITY = 0.35
const fractionDigits = computed(() => (props.metric === 'harmonized' ? 1 : 0))
const valueFormat = computed(
  () => new Intl.NumberFormat('en-US', { maximumFractionDigits: fractionDigits.value }),
)
const pctFormat = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0,
  signDisplay: 'exceptZero',
})
const median = computed(() => completeYearMedian(props.rows, props.metric))

function tooltipHtml(index: number): string {
  const row = props.rows[index]
  if (!row) return ''
  const format = (value: number) => valueFormat.value.format(value)
  const lines = [`<div style="font-weight:600">${row.year}</div>`]
  if (props.metric === 'raw') {
    lines.push(
      `<div style="margin-top:2px;color:#ffe066">${format(row.total_hotspots)} detections</div>`,
      `<div style="color:#cbd5e1">MODIS: ${format(row.modis_count)}</div>`,
      `<div style="color:#cbd5e1">VIIRS: ${format(row.viirs_count)}</div>`,
    )
  } else {
    lines.push(
      `<div style="margin-top:2px;color:#ffe066">${format(row.harmonized_index)} harmonized index</div>`,
      `<div style="color:#cbd5e1">${valueFormat.value.format(row.total_hotspots)} raw detections</div>`,
    )
  }
  const value = annualValue(row, props.metric)
  if (!row.complete) {
    lines.push(
      `<div style="margin-top:6px;color:#94a3b8">Incomplete year: ${row.months_in_archive} of 12 months in the archive</div>`,
    )
  } else if (median.value !== null && median.value > 0) {
    const pct = ((value - median.value) / median.value) * 100
    lines.push(
      `<div style="margin-top:6px;color:#f3f4f6">${pctFormat.format(pct)}% vs. median year</div>`,
    )
  }
  return lines.join('')
}

function barItem(value: number, row: AnnualRow, color: string, isTop: boolean) {
  return {
    value,
    itemStyle: {
      color,
      opacity: row.complete ? 1 : PARTIAL_OPACITY,
      borderRadius: isTop ? [3, 3, 0, 0] : 0,
    },
    label: {
      show: isTop && !row.complete,
      position: 'top',
      distance: 4,
      color: '#cbd5e1',
      opacity: 1,
      fontSize: 10,
      formatter: 'Partial',
    },
  }
}

const chartOption = computed(() => {
  const years = props.rows.map((row) => String(row.year))
  const medianLine =
    median.value === null
      ? undefined
      : {
          symbol: 'none',
          silent: true,
          lineStyle: { color: '#cbd5e1', width: 1.5, type: [5, 4] },
          label: {
            position: 'insideStartTop',
            color: '#cbd5e1',
            fontSize: 11,
            formatter: 'Median year',
          },
          data: [{ yAxis: median.value }],
        }
  const viirsLine =
    props.metric === 'raw' && props.rows.some((row) => row.year === VIIRS_FIRST_YEAR)
      ? {
          xAxis: String(VIIRS_FIRST_YEAR),
          lineStyle: { color: 'rgba(230, 159, 0, 0.55)', width: 1, type: 'dotted' },
          label: {
            position: 'end',
            distance: 6,
            rotate: 0,
            color: '#e6b04d',
            fontSize: 11,
            formatter: 'VIIRS starts',
          },
        }
      : null

  const series =
    props.metric === 'raw'
      ? [
          {
            name: 'MODIS',
            type: 'bar',
            stack: 'sensors',
            barMaxWidth: 28,
            data: props.rows.map((row) =>
              barItem(row.modis_count, row, SERIES_COLORS.modis, row.viirs_count === 0),
            ),
          },
          {
            name: 'VIIRS',
            type: 'bar',
            stack: 'sensors',
            barMaxWidth: 28,
            data: props.rows.map((row) =>
              barItem(row.viirs_count, row, SERIES_COLORS.viirs, row.viirs_count > 0),
            ),
            markLine: medianLine && {
              ...medianLine,
              data: viirsLine ? [...medianLine.data, viirsLine] : medianLine.data,
            },
          },
        ]
      : [
          {
            name: 'Harmonized index',
            type: 'bar',
            barMaxWidth: 28,
            data: props.rows.map((row) =>
              barItem(row.harmonized_index, row, SERIES_COLORS.harmonized, true),
            ),
            markLine: medianLine,
          },
        ]

  return {
    animationDuration: 200,
    grid: { top: 36, right: 16, bottom: 28, left: 52 },
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
      data: years,
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
    series,
  }
})
</script>

<template>
  <div role="img" :aria-label="description" class="h-[20rem] w-full">
    <VChart :option="chartOption" autoresize aria-hidden="true" />
  </div>
</template>
