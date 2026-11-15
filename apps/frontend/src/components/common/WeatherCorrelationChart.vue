<script lang="ts">
export interface WeatherCorrelationRecord {
  date: string
  is_complete: boolean
  wind_speed: number | null
  wind_direction_from_deg: number | null
  wind_direction_to_deg: number | null
  wind_u: number | null
  wind_v: number | null
  temperature: number | null
  humidity: number | null
  precipitation: number | null
  wind_fire_angle_diff_deg: number | null
  wind_fire_alignment_cos: number | null
  status_message: string
}

export interface RawWeatherRecord {
  date: string
  T2M?: number | null
  RH2M?: number | null
  WS10M?: number | null
  WD10M?: number | null
  PRECTOTCORR?: number | null
}

export function formatNasaDate(raw: string): string {
  if (raw.length === 8) {
    return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
  }
  return raw
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, LineChart, GridComponent, MarkLineComponent, TooltipComponent])

const props = defineProps<{
  correlationRows: readonly WeatherCorrelationRecord[]
  weatherRows: readonly RawWeatherRecord[]
  mode: 'alignment' | 'meteo'
  fireDirectionDeg: number
  description: string
}>()

const decFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })

function tooltipHtml(index: number): string {
  const corr = props.correlationRows[index]
  const raw = props.weatherRows[index]
  const dateStr = formatNasaDate(corr?.date ?? raw?.date ?? '')
  if (props.mode === 'alignment' && corr) {
    return [
      `<div style="font-weight:600">${dateStr} · Wind vs. Fire (${props.fireDirectionDeg}°)</div>`,
      `<div style="margin-top:3px;color:#ffe066">Alignment cos(Δθ): ${corr.wind_fire_alignment_cos !== null ? corr.wind_fire_alignment_cos.toFixed(3) : '—'} (Δθ = ${corr.wind_fire_angle_diff_deg !== null ? `${corr.wind_fire_angle_diff_deg.toFixed(1)}°` : '—'})</div>`,
      `<div style="color:#38bdf8">Wind speed: ${corr.wind_speed !== null ? `${decFmt.format(corr.wind_speed)} m/s` : '—'}</div>`,
      `<div style="color:#cbd5e1">Wind blows toward: ${corr.wind_direction_to_deg !== null ? `${corr.wind_direction_to_deg.toFixed(0)}°` : '—'} (from ${corr.wind_direction_from_deg !== null ? `${corr.wind_direction_from_deg.toFixed(0)}°` : '—'})</div>`,
      `<div style="color:#94a3b8">Vector (u, v): (${corr.wind_u?.toFixed(2) ?? '—'}, ${corr.wind_v?.toFixed(2) ?? '—'}) m/s</div>`,
    ].join('')
  }
  const t2m = raw?.T2M ?? corr?.temperature ?? null
  const rh = raw?.RH2M ?? corr?.humidity ?? null
  const prec = raw?.PRECTOTCORR ?? corr?.precipitation ?? null
  return [
    `<div style="font-weight:600">${dateStr} · NASA POWER Daily</div>`,
    `<div style="margin-top:3px;color:#e69f00">Temperature (T2M): ${t2m !== null ? `${decFmt.format(t2m)} °C` : '—'}</div>`,
    `<div style="color:#38bdf8">Relative Humidity (RH2M): ${rh !== null ? `${decFmt.format(rh)} %` : '—'}</div>`,
    `<div style="color:#cbd5e1">Precipitation (PRECTOTCORR): ${prec !== null ? `${decFmt.format(prec)} mm` : '—'}</div>`,
  ].join('')
}

const chartOption = computed(() => {
  const labels = props.correlationRows.map((r) => formatNasaDate(r.date).slice(5))

  if (props.mode === 'alignment') {
    const speeds = props.correlationRows.map((r) => r.wind_speed)
    const cosines = props.correlationRows.map((r) => r.wind_fire_alignment_cos)
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
        axisLabel: { color: '#94a3b8', fontSize: 10 },
      },
      yAxis: [
        {
          type: 'value',
          name: 'Wind (m/s)',
          nameTextStyle: { color: '#38bdf8', fontSize: 10 },
          axisLabel: { color: '#94a3b8', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
        },
        {
          type: 'value',
          min: -1,
          max: 1,
          name: 'Alignment cos(Δθ)',
          nameTextStyle: { color: '#ffe066', fontSize: 10 },
          axisLabel: { color: '#ffe066', fontSize: 10 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: 'Wind speed (m/s)',
          type: 'bar',
          barMaxWidth: 24,
          itemStyle: { color: 'rgba(56, 189, 248, 0.55)', borderRadius: [3, 3, 0, 0] },
          data: speeds,
        },
        {
          name: 'Wind-Fire alignment cos(Δθ)',
          type: 'line',
          yAxisIndex: 1,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: { color: '#e69f00' },
          lineStyle: { color: '#e69f00', width: 2.2 },
          markLine: {
            symbol: 'none',
            silent: true,
            lineStyle: { color: 'rgba(255,255,255,0.2)', type: 'dashed' },
            data: [{ yAxis: 0 }],
          },
          data: cosines,
        },
      ],
    }
  }

  const temps = props.correlationRows.map(
    (r, i) => props.weatherRows[i]?.T2M ?? r.temperature ?? null,
  )
  const humidities = props.correlationRows.map(
    (r, i) => props.weatherRows[i]?.RH2M ?? r.humidity ?? null,
  )
  const precip = props.correlationRows.map(
    (r, i) => props.weatherRows[i]?.PRECTOTCORR ?? r.precipitation ?? null,
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
      axisLabel: { color: '#94a3b8', fontSize: 10 },
    },
    yAxis: [
      {
        type: 'value',
        name: '°C / mm',
        nameTextStyle: { color: '#94a3b8', fontSize: 10 },
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)', type: 'dashed' } },
      },
      {
        type: 'value',
        min: 0,
        max: 100,
        name: 'Humidity (%)',
        nameTextStyle: { color: '#38bdf8', fontSize: 10 },
        axisLabel: { color: '#38bdf8', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'Precipitation (mm)',
        type: 'bar',
        barMaxWidth: 24,
        itemStyle: { color: 'rgba(148, 163, 184, 0.45)', borderRadius: [3, 3, 0, 0] },
        data: precip,
      },
      {
        name: 'Temperature T2M (°C)',
        type: 'line',
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#e69f00' },
        lineStyle: { color: '#e69f00', width: 2.2 },
        data: temps,
      },
      {
        name: 'Relative Humidity RH2M (%)',
        type: 'line',
        yAxisIndex: 1,
        symbol: 'diamond',
        symbolSize: 5,
        itemStyle: { color: '#38bdf8' },
        lineStyle: { color: '#38bdf8', width: 1.8, type: 'dashed' },
        data: humidities,
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
