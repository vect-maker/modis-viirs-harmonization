<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ECElementEvent } from 'echarts/core'
import VChart from 'vue-echarts'
import type { CalendarCell } from '@/types/calendar'
import { calendarColor } from '@/utils/historicalCalendar'

use([CanvasRenderer, HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent])

const props = defineProps<{
  rows: { year: number; cells: CalendarCell[] }[]
  maxCount: number
  selectedPeriod: { year: number; month: number } | null
}>()

const emit = defineEmits<{ select: [year: number, month: number] }>()

const monthFormatter = new Intl.DateTimeFormat('en-US', { month: 'short', timeZone: 'UTC' })
const months = Array.from({ length: 12 }, (_, i) =>
  monthFormatter.format(new Date(Date.UTC(2024, i, 1))),
)
const compactNumber = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
})

const chartHeightPx = computed(() => Math.max(240, props.rows.length * 28 + 44))

const chartOption = computed(() => {
  const years = props.rows.map((row) => String(row.year))
  const data = props.rows.flatMap((row, yearIdx) =>
    row.cells.map((cell, monthIdx) => {
      const selected =
        props.selectedPeriod?.year === cell.year && props.selectedPeriod?.month === cell.month
      return {
        value: [monthIdx, yearIdx, cell.count ?? -1] as [number, number, number],
        year: cell.year,
        month: cell.month,
        count: cell.count,
        itemStyle: {
          color: calendarColor(cell.count, props.maxCount),
          borderColor: selected ? '#ffffff' : '#0b0f14',
          borderWidth: selected ? 2 : 1.5,
          borderRadius: 4,
        },
      }
    }),
  )

  return {
    animation: false,
    grid: {
      top: 28,
      right: 8,
      bottom: 8,
      left: 48,
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#11161d',
      borderColor: '#28323e',
      borderWidth: 1,
      textStyle: {
        color: '#f3f4f6',
        fontSize: 12,
      },
      formatter(params: unknown) {
        const item = params as { data?: { year?: number; month?: number; count?: number | null } }
        const year = item.data?.year
        const month = item.data?.month
        const count = item.data?.count
        if (!year || !month) return ''
        const label = `${months[month - 1]} ${year}`
        const detail =
          count === null || count === undefined
            ? 'No records · coverage unverified'
            : `${count.toLocaleString()} observed detections`
        return `<div class="font-medium">${label}</div><div class="mt-0.5 text-amber-400 font-mono">${detail}</div>`
      },
    },
    xAxis: {
      type: 'category',
      position: 'top',
      data: months,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#9ca3af',
        fontSize: 11,
      },
      splitArea: { show: false },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: years,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#cbd5e1',
        fontSize: 11,
        fontFamily: 'monospace',
      },
      splitArea: { show: false },
    },
    visualMap: {
      show: false,
      min: -1,
      max: props.maxCount,
    },
    series: [
      {
        name: 'Monthly Detections',
        type: 'heatmap',
        data,
        label: {
          show: true,
          fontSize: 10,
          color: '#ffedd5',
          formatter(params: unknown) {
            const item = params as { data?: { count?: number | null } }
            const count = item.data?.count
            return count === null || count === undefined ? '—' : compactNumber.format(count)
          },
        },
        emphasis: {
          itemStyle: {
            borderColor: '#ffffff',
            borderWidth: 1.5,
          },
        },
      },
    ],
  }
})

function onChartClick(params: ECElementEvent) {
  const data = params.data as { year?: number; month?: number } | undefined
  if (typeof data?.year === 'number' && typeof data?.month === 'number') {
    emit('select', data.year, data.month)
  }
}
</script>

<template>
  <div
    class="max-h-72 overflow-y-auto rounded-lg border border-white/10 p-1"
    tabindex="0"
    role="region"
    aria-label="Historical monthly detections heatmap. Click a month cell to inspect totals."
  >
    <div class="w-full" :style="{ height: `${chartHeightPx}px` }">
      <VChart
        class="h-full w-full"
        :option="chartOption"
        autoresize
        @click="onChartClick"
      />
    </div>
  </div>
</template>
