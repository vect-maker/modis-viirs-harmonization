<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps<{
  importances: Readonly<Record<string, number>>
  description: string
}>()

const FEATURE_LABELS: Record<string, string> = {
  latitude: 'Latitude',
  longitude: 'Longitude',
  total_frp: 'Total FRP (MW)',
  hotspot_count: 'Hotspot Count',
  wind_speed: 'Wind Speed (m/s)',
  wind_u: 'Wind East-West (u)',
  wind_v: 'Wind North-South (v)',
  humidity: 'Relative Humidity (%)',
  temperature: 'Temperature (°C)',
  prev_speed_kmh: 'Previous Speed (km/h)',
}

const sortedEntries = computed(() =>
  Object.entries(props.importances)
    .map(([key, val]) => ({
      key,
      label: FEATURE_LABELS[key] ?? key,
      pct: Number((val * 100).toFixed(1)),
    }))
    .sort((a, b) => a.pct - b.pct),
)

const chartOption = computed(() => {
  const labels = sortedEntries.value.map((e) => e.label)
  const values = sortedEntries.value.map((e, idx) => ({
    value: e.pct,
    itemStyle: {
      color: idx >= sortedEntries.value.length - 3 ? '#e69f00' : '#38bdf8',
      borderRadius: [0, 3, 3, 0],
    },
  }))

  return {
    animationDuration: 200,
    grid: { top: 12, right: 36, bottom: 24, left: 136 },
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
        const entry =
          first?.dataIndex !== undefined ? sortedEntries.value[first.dataIndex] : undefined
        if (!entry) return ''
        return `<div style="font-weight:600">${entry.label}</div><div style="color:#ffe066">Importance: ${entry.pct.toFixed(1)}%</div>`
      },
    },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8', fontSize: 10, formatter: (v: number) => `${v}%` },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
      axisTick: { show: false },
      axisLabel: { color: '#cbd5e1', fontSize: 11 },
    },
    series: [
      {
        name: 'Feature importance',
        type: 'bar',
        barMaxWidth: 16,
        data: values,
      },
    ],
  }
})
</script>

<template>
  <div role="img" :aria-label="description" class="h-[17rem] w-full">
    <VChart :option="chartOption" autoresize aria-hidden="true" />
  </div>
</template>
