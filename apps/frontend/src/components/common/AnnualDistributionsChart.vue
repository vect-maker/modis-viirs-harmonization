<script lang="ts">
export type DistributionVariable = 'frp' | 'confidence' | 'bright_tir' | 'bright_mir'

export interface DescriptiveStats {
  count: number
  sum: number | null
  mean: number | null
  std: number | null
  min: number | null
  p25: number | null
  median: number | null
  p75: number | null
  p90: number | null
  iqr: number | null
  max: number | null
}

export interface AnnualDistributionRow {
  year: number
  complete: boolean
  provisional_months: number
  total_hotspots: number
  frp: DescriptiveStats | null
  confidence: DescriptiveStats | null
  bright_tir: DescriptiveStats | null
  bright_mir: DescriptiveStats | null
}

export const VARIABLE_META: Record<
  DistributionVariable,
  { label: string; unit: string; digits: number }
> = {
  frp: { label: 'Fire Radiative Power (FRP)', unit: 'MW', digits: 1 },
  confidence: { label: 'Detection Confidence', unit: '%', digits: 1 },
  bright_tir: { label: 'Thermal Infrared Brightness (TIR)', unit: 'K', digits: 1 },
  bright_mir: { label: 'Mid-Infrared Brightness (MIR)', unit: 'K', digits: 1 },
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { useLocaleFormatters } from '@/i18n'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent])

const { t } = useI18n()
const { bcp47Locale } = useLocaleFormatters()

const props = defineProps<{
  rows: readonly AnnualDistributionRow[]
  variable: DistributionVariable
  description: string
}>()

const meta = computed(() => VARIABLE_META[props.variable])
const varLabel = computed(() => t(`charts.distributions.vars.${props.variable}`))
const fmt = computed(
  () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: meta.value.digits }),
)
const intFmt = computed(
  () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 0 }),
)

function formatVal(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return `${fmt.value.format(val)} ${meta.value.unit}`
}

function tooltipHtml(index: number): string {
  const row = props.rows[index]
  if (!row) return ''
  const stat = row[props.variable]
  if (!stat || stat.count === 0) {
    return `<div style="font-weight:600">${row.year}</div><div style="color:#94a3b8">${t('charts.distributions.noObservations')}</div>`
  }
  return [
    `<div style="font-weight:600">${row.year} · ${varLabel.value}</div>`,
    `<div style="margin-top:4px;color:#ffe066">${t('charts.distributions.median', { val: formatVal(stat.median) })}</div>`,
    `<div style="color:#38bdf8">${t('charts.distributions.mean', { val: formatVal(stat.mean), sd: formatVal(stat.std) })}</div>`,
    `<div style="color:#cbd5e1">${t('charts.distributions.iqr', { p25: formatVal(stat.p25), p75: formatVal(stat.p75) })}</div>`,
    `<div style="color:#e69f00">${t('charts.distributions.p90Max', { p90: formatVal(stat.p90), max: formatVal(stat.max) })}</div>`,
    `<div style="margin-top:4px;color:#94a3b8">${t('charts.distributions.observations', { count: intFmt.value.format(stat.count) })}</div>`,
  ].join('')
}

const chartOption = computed(() => {
  const years = props.rows.map((r) => String(r.year))
  const stats = props.rows.map((r) => r[props.variable])

  const p25Base = stats.map((s) => (s && s.p25 !== null ? s.p25 : null))
  const iqrSpan = stats.map((s) =>
    s && s.p25 !== null && s.p75 !== null ? Math.max(0, s.p75 - s.p25) : null,
  )
  const medians = stats.map((s) => s?.median ?? null)
  const means = stats.map((s) => s?.mean ?? null)
  const p90s = stats.map((s) => s?.p90 ?? null)

  // Para temperaturas en Kelvin (280–400 K), ajustamos el eje Y a los datos reales.
  const isKelvin = props.variable === 'bright_tir' || props.variable === 'bright_mir'

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
      data: years,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      scale: isKelvin,
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (v: number) => `${fmt.value.format(v)}`,
      },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
    },
    series: [
      {
        name: 'IQR Floor',
        type: 'line',
        stack: 'iqr',
        data: p25Base,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        silent: true,
        z: 1,
      },
      {
        name: 'IQR (P25–P75)',
        type: 'line',
        stack: 'iqr',
        data: iqrSpan,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(230, 159, 0, 0.18)' },
        silent: true,
        z: 1,
      },
      {
        name: 'Median (P50)',
        type: 'line',
        data: medians,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#e69f00' },
        lineStyle: { color: '#e69f00', width: 2.5 },
        z: 3,
      },
      {
        name: 'Mean',
        type: 'line',
        data: means,
        symbol: 'diamond',
        symbolSize: 6,
        itemStyle: { color: '#38bdf8' },
        lineStyle: { color: '#38bdf8', width: 1.75, type: 'dashed' },
        z: 3,
      },
      {
        name: 'P90',
        type: 'line',
        data: p90s,
        symbol: 'none',
        lineStyle: { color: '#ffe066', width: 1.5, type: 'dotted' },
        z: 2,
      },
    ],
  }
})
</script>

<template>
  <div role="img" :aria-label="description" class="h-[21rem] w-full">
    <VChart :option="chartOption" autoresize aria-hidden="true" />
  </div>
</template>
