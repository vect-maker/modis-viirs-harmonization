<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { parseDate } from '@internationalized/date'
import { useLocaleFormatters } from '@/i18n'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  MarkAreaComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ECElementEvent } from 'echarts/core'
import VChart from 'vue-echarts'
import type { DailyHotspotActivity } from '@/types/hotspot'
import type { HotspotDateRange } from '@/types/filters'
import { getChartColors } from '@/utils/themeColors'

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  MarkAreaComponent,
])

const props = defineProps<{
  days: DailyHotspotActivity[]
  selectedRange: HotspotDateRange | null
}>()

const emit = defineEmits<{ select: [date: string] }>()

const { t } = useI18n()
const { bcp47Locale, formatInt } = useLocaleFormatters()
const chartColors = computed(() => getChartColors())

const axisFormatter = computed(
  () =>
    new Intl.DateTimeFormat(bcp47Locale.value, {
      month: 'short',
      day: 'numeric',
      year: '2-digit',
      timeZone: 'UTC',
    }),
)

const tooltipFormatter = computed(
  () =>
    new Intl.DateTimeFormat(bcp47Locale.value, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone: 'UTC',
    }),
)

function formatUtcDate(dateStr: string, formatter: Intl.DateTimeFormat): string {
  return formatter.format(parseDate(dateStr).toDate('UTC'))
}

const showSlider = computed(() => props.days.length > 1)

const chartOption = computed(() => {
  const colors = chartColors.value
  const range = props.selectedRange
  const dates = props.days.map((day) => day.date)
  const lastIndex = Math.max(0, props.days.length - 1)
  const points = props.days.map((day) => {
    const isSelected = !range || (day.date >= range.start && day.date <= range.end)
    return {
      value: day.count,
      symbolSize: day.count > 0 ? 7 : 3,
      itemStyle: {
        color: isSelected ? colors.barActive : colors.barDimmed,
        borderColor: '#11161d',
        borderWidth: 1,
      },
    }
  })

  const markAreaData = range
    ? [[{ xAxis: range.start }, { xAxis: range.end }]]
    : []

  const dataZoom = showSlider.value
    ? [
        {
          type: 'inside',
          xAxisIndex: 0,
          startValue: 0,
          endValue: lastIndex,
        },
        {
          type: 'slider',
          xAxisIndex: 0,
          height: 20,
          bottom: 6,
          startValue: 0,
          endValue: lastIndex,
          borderColor: 'rgba(255, 255, 255, 0.12)',
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          fillerColor: 'rgba(230, 159, 0, 0.18)',
          handleStyle: {
            color: '#e69f00',
            borderColor: '#e69f00',
          },
          moveHandleStyle: {
            color: 'rgba(230, 159, 0, 0.6)',
          },
          dataBackground: {
            lineStyle: { color: 'rgba(230, 159, 0, 0.45)', width: 1 },
            areaStyle: { color: 'rgba(230, 159, 0, 0.12)' },
          },
          selectedDataBackground: {
            lineStyle: { color: '#e69f00', width: 1 },
            areaStyle: { color: 'rgba(230, 159, 0, 0.28)' },
          },
          textStyle: {
            color: '#9ca3af',
            fontSize: 10,
          },
          labelFormatter: (_value: number, valueStr: string) =>
            valueStr ? formatUtcDate(valueStr, axisFormatter.value) : '',
        },
      ]
    : []

  return {
    animationDuration: 250,
    grid: {
      top: 14,
      right: 14,
      bottom: showSlider.value ? 52 : 26,
      left: 44,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: { color: 'rgba(230, 159, 0, 0.45)', type: 'dashed' },
      },
      backgroundColor: '#11161d',
      borderColor: '#28323e',
      borderWidth: 1,
      textStyle: {
        color: '#f3f4f6',
        fontSize: 12,
      },
      formatter(params: unknown) {
        const list = Array.isArray(params) ? params : [params]
        const first = list[0] as { dataIndex?: number } | undefined
        const day = first?.dataIndex !== undefined ? props.days[first.dataIndex] : undefined
        if (!day) return ''
        const label = formatUtcDate(day.date, tooltipFormatter.value)
        const count = formatInt(day.count)
        return `<div class="font-medium">${label} · UTC</div><div class="mt-0.5 text-amber-400 font-mono">${t('dashboard.timeline.tooltipDetections', { count })}</div>`
      },
    },
    xAxis: {
      type: 'category',
      boundaryGap: props.days.length <= 1,
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#9ca3af',
        fontSize: 10,
        formatter: (value: string) => formatUtcDate(value, axisFormatter.value),
      },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: {
        color: '#9ca3af',
        fontSize: 10,
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.08)',
          type: 'dashed',
        },
      },
    },
    dataZoom,
    series: [
      {
        name: 'Detections',
        type: 'line',
        smooth: false,
        showAllSymbol: true,
        symbol: 'circle',
        lineStyle: {
          color: colors.barActive,
          width: 2,
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(230, 159, 0, 0.28)' },
              { offset: 1, color: 'rgba(230, 159, 0, 0.02)' },
            ],
          },
        },
        markArea: range
          ? {
              silent: true,
              itemStyle: { color: 'rgba(230, 159, 0, 0.12)' },
              data: markAreaData,
            }
          : undefined,
        data: points,
      },
    ],
  }
})

function onChartClick(params: ECElementEvent) {
  const day = typeof params.dataIndex === 'number' ? props.days[params.dataIndex] : undefined
  if (day) emit('select', day.date)
}
</script>

<template>
  <div
    v-if="days.length"
    role="region"
    aria-label="Daily detections timeline. Drag the slider to zoom or click a day to filter the map."
    class="h-44 w-full"
  >
    <VChart class="h-full w-full" :option="chartOption" autoresize @click="onChartClick" />
  </div>
  <p v-else role="status" class="py-5 text-center text-sm text-ink-muted">
    No dated records are available.
  </p>
</template>
