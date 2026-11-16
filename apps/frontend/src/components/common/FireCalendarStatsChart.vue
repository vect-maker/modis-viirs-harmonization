<script lang="ts">
export interface FireCalendarIntervalItem {
  date: string
  hotspot_count: number
  fire_count: number
  new_fires: number
  active_fires: number
  frp_total: number
  frp_average: number
  max_frp: number
  daytime_hotspots: number
  nighttime_hotspots: number
  high_confidence_count: number
  missing?: boolean
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
  intervals: readonly FireCalendarIntervalItem[]
  aggregation: 'day' | 'week' | 'month'
  description: string
}>()

const intFmt = computed(
  () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 0 }),
)
const frpFmt = computed(
  () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 1 }),
)

function tooltipHtml(index: number): string {
  const item = props.intervals[index]
  if (!item) return ''
  if (item.missing) {
    return [
      `<div style="font-weight:600">${item.date}</div>`,
      `<div style="margin-top:3px;color:#94a3b8">${t('charts.fireCalendar.tooltipMissing')}</div>`,
    ].join('')
  }
  return [
    `<div style="font-weight:600">${item.date}</div>`,
    `<div style="margin-top:3px;color:#ffe066">${t('charts.fireCalendar.tooltipHotspots', { total: intFmt.value.format(item.hotspot_count), high: intFmt.value.format(item.high_confidence_count) })}</div>`,
    `<div style="color:#e69f00">${t('charts.fireCalendar.tooltipDay', { count: intFmt.value.format(item.daytime_hotspots) })}</div>`,
    `<div style="color:#38bdf8">${t('charts.fireCalendar.tooltipNight', { count: intFmt.value.format(item.nighttime_hotspots) })}</div>`,
    `<div style="margin-top:4px;color:#cbd5e1">${t('charts.fireCalendar.tooltipAvgMax', { avg: frpFmt.value.format(item.frp_average), max: frpFmt.value.format(item.max_frp) })}</div>`,
    `<div style="color:#94a3b8">${t('charts.fireCalendar.tooltipTotalFrp', { total: frpFmt.value.format(item.frp_total) })}</div>`,
  ].join('')
}

const chartOption = computed(() => {
  const labels = props.intervals.map((item) =>
    props.aggregation === 'month' ? item.date.slice(0, 7) : item.date,
  )
  const dayData = props.intervals.map((item) => (item.missing ? null : item.daytime_hotspots))
  const nightData = props.intervals.map((item) => (item.missing ? null : item.nighttime_hotspots))
  const avgFrpData = props.intervals.map((item) =>
    item.missing ? null : Number(item.frp_average.toFixed(2)),
  )

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
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value',
        name: t('charts.fireCalendar.yAxisHotspots'),
        nameTextStyle: { color: '#94a3b8', fontSize: 10 },
        axisLabel: {
          color: '#94a3b8',
          fontSize: 10,
          formatter: (v: number) =>
            new Intl.NumberFormat(bcp47Locale.value, { notation: 'compact' }).format(v),
        },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
      },
      {
        type: 'value',
        name: t('charts.fireCalendar.yAxisAvgFrp'),
        nameTextStyle: { color: '#ffe066', fontSize: 10 },
        axisLabel: {
          color: '#ffe066',
          fontSize: 10,
          formatter: (v: number) => `${frpFmt.value.format(v)}`,
        },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: t('charts.fireCalendar.seriesDay'),
        type: 'bar',
        stack: 'daynight',
        barMaxWidth: 28,
        itemStyle: { color: '#e69f00' },
        data: dayData,
      },
      {
        name: t('charts.fireCalendar.seriesNight'),
        type: 'bar',
        stack: 'daynight',
        barMaxWidth: 28,
        itemStyle: { color: '#38bdf8', borderRadius: [3, 3, 0, 0] },
        data: nightData,
      },
      {
        name: t('charts.fireCalendar.seriesAvgFrp'),
        type: 'line',
        yAxisIndex: 1,
        symbol: 'circle',
        symbolSize: 5,
        itemStyle: { color: '#ffe066' },
        lineStyle: { color: '#ffe066', width: 2 },
        data: avgFrpData,
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
