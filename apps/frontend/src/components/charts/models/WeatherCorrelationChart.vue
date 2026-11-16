<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import { useModelChartsApi } from '@/api'
import { useApiFetch } from '@/api/useApiFetch'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useChartFiltersStore } from '@/stores/chartFilters'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseChartLoading from '@/components/ui/BaseChartLoading.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import WeatherCorrelationRenderer, {
  formatNasaDate,
  type RawWeatherRecord,
} from '@/components/common/WeatherCorrelationChart.vue'

const filtersStore = useChartFiltersStore()
const { activePolygon, selectedYear, activeClusterContext } = storeToRefs(filtersStore)
const { dateRange } = storeToRefs(useHotspotsStore())
const { getWeatherCorrelation } = useModelChartsApi()

const MS_PER_DAY = 86_400_000

function resolveWeatherWindow(
  year: number,
  range: { start: string; end: string } | null,
): { startDate: string; endDate: string } {
  if (range && Number(range.end.slice(0, 4)) === year) {
    const startMs = Date.parse(`${range.start}T00:00:00Z`)
    const endMs = Date.parse(`${range.end}T00:00:00Z`)
    if (!Number.isNaN(startMs) && !Number.isNaN(endMs)) {
      const yearStartMs = Date.UTC(year, 0, 1)
      const clampedStart =
        endMs > startMs
          ? Math.max(yearStartMs, startMs)
          : Math.max(yearStartMs, endMs - 14 * MS_PER_DAY)
      const clampedEnd =
        endMs > startMs ? Math.min(endMs, clampedStart + 14 * MS_PER_DAY) : endMs
      const startIso = new Date(clampedStart).toISOString().slice(0, 10)
      const endIso = new Date(clampedEnd).toISOString().slice(0, 10)
      return {
        startDate: `${startIso}T00:00:00`,
        endDate: `${endIso}T23:59:59`,
      }
    }
  }
  const mo = year === 2026 ? '05' : '04'
  return {
    startDate: `${year}-${mo}-01T00:00:00`,
    endDate: `${year}-${mo}-15T23:59:59`,
  }
}

const RawWeatherResponseSchema = z.object({
  data: z.array(
    z.object({
      date: z.string(),
      T2M: z.number().nullable().optional(),
      RH2M: z.number().nullable().optional(),
      WS10M: z.number().nullable().optional(),
      WD10M: z.number().nullable().optional(),
      PRECTOTCORR: z.number().nullable().optional(),
    }),
  ),
})

const LOCATION_PRESETS = [
  { value: '16.92,-90.25', label: 'Petén, Guatemala (16.9°N, 90.3°W)' },
  { value: '14.80,-86.10', label: 'Olancho, Honduras (14.8°N, 86.1°W)' },
  { value: '14.10,-84.20', label: 'RACCN, Nicaragua (14.1°N, 84.2°W)' },
  { value: '10.45,-85.40', label: 'Guanacaste, Costa Rica (10.5°N, 85.4°W)' },
  { value: '8.40,-77.95', label: 'Darién, Panama (8.4°N, 78.0°W)' },
] as const

const DIRECTION_OPTIONS = [
  { value: '270', label: 'West (270°)' },
  { value: '315', label: 'NW (315°)' },
  { value: '0', label: 'North (0°)' },
  { value: '90', label: 'East (90°)' },
] as const

const VIEW_OPTIONS = [
  { value: 'alignment', label: 'Wind-Fire Alignment' },
  { value: 'meteo', label: 'NASA POWER Daily (T2M / RH2M)' },
] as const

const SOURCE_OPTIONS = [
  { value: 'cluster', label: 'Active Fire Cluster' },
  { value: 'preset', label: 'Reference Location' },
] as const

const presetLocation = shallowRef<string>('16.92,-90.25')
const fireDirection = shallowRef<'270' | '315' | '0' | '90'>('270')
const viewMode = shallowRef<'alignment' | 'meteo'>('alignment')
const sourceMode = shallowRef<'cluster' | 'preset'>('cluster')

const usingCluster = computed(
  () => sourceMode.value === 'cluster' && activeClusterContext.value != null,
)

const activeTarget = computed(() => {
  const clusterCtx = activeClusterContext.value
  if (usingCluster.value && clusterCtx) {
    return {
      latitude: clusterCtx.latitude,
      longitude: clusterCtx.longitude,
      startDate: clusterCtx.startDate,
      endDate: clusterCtx.endDate,
      directionDeg: clusterCtx.directionDeg,
      fromPolygon: false,
      fromCluster: true,
      clusterId: clusterCtx.fireId,
    }
  }
  const { startDate, endDate } = resolveWeatherWindow(selectedYear.value, dateRange.value)

  if (activePolygon.value) {
    const ring = activePolygon.value.coordinates[0]
    if (ring && ring.length > 0) {
      const sumLon = ring.reduce((acc, pt) => acc + (pt[0] ?? 0), 0)
      const sumLat = ring.reduce((acc, pt) => acc + (pt[1] ?? 0), 0)
      return {
        latitude: Number((sumLat / ring.length).toFixed(4)),
        longitude: Number((sumLon / ring.length).toFixed(4)),
        startDate,
        endDate,
        directionDeg: Number(fireDirection.value),
        fromPolygon: true,
        fromCluster: false,
        clusterId: null,
      }
    }
  }
  const [latStr, lonStr] = presetLocation.value.split(',')
  return {
    latitude: Number(latStr ?? 16.92),
    longitude: Number(lonStr ?? -90.25),
    startDate,
    endDate,
    directionDeg: Number(fireDirection.value),
    fromPolygon: false,
    fromCluster: false,
    clusterId: null,
  }
})

const {
  data: bundle,
  isLoading,
  error,
  refresh,
} = useChartLifecycle({
  fetcher: async () => {
    const { latitude, longitude, startDate, endDate, directionDeg } = activeTarget.value
    const [correlation, rawFetch] = await Promise.all([
      getWeatherCorrelation({
        latitude,
        longitude,
        start_date: startDate.slice(0, 10),
        end_date: endDate.slice(0, 10),
        fire_direction_deg: directionDeg,
        limit: 50,
        offset: 0,
      }),
      useApiFetch('/weather?limit=50&offset=0')
        .post({
          latitude,
          longitude,
          start: startDate,
          end: endDate,
          parameters: 'T2M,RH2M,WS10M,WD10M,PRECTOTCORR',
          community: 'AG',
        })
        .json(),
    ])
    let weatherRows: readonly RawWeatherRecord[] = []
    if (rawFetch.data.value) {
      const parsedRaw = RawWeatherResponseSchema.safeParse(rawFetch.data.value)
      weatherRows = parsedRaw.success ? parsedRaw.data.data : []
    }
    return { correlation, weatherRows }
  },
  watchSources: [
    presetLocation,
    fireDirection,
    sourceMode,
    selectedYear,
    dateRange,
    activePolygon,
    activeClusterContext,
  ],
})

const correlationResult = computed(() => bundle.value?.correlation ?? null)
const weatherRows = computed(() => bundle.value?.weatherRows ?? [])
const rows = computed(() => correlationResult.value?.records ?? [])
const isEmpty = computed(() => correlationResult.value !== null && rows.value.length === 0)

const summaryText = computed(() => {
  const valid = rows.value.filter((r) => r.wind_fire_alignment_cos !== null)
  if (valid.length === 0) return 'No complete wind observations returned for this period.'
  const meanCos =
    valid.reduce((sum, r) => sum + (r.wind_fire_alignment_cos ?? 0), 0) / valid.length
  const meanWind = valid.reduce((sum, r) => sum + (r.wind_speed ?? 0), 0) / valid.length
  const alignedDays = valid.filter((r) => (r.wind_fire_alignment_cos ?? 0) > 0.5).length
  const prefix = activeTarget.value.fromCluster
    ? `Synced with Fire Cluster #${activeTarget.value.clusterId}: across`
    : 'Across'
  return `${prefix} ${valid.length} days at (${activeTarget.value.latitude}°, ${activeTarget.value.longitude}°), mean 10 m wind speed was ${meanWind.toFixed(1)} m/s with ${alignedDays} days strongly aligned (cos Δθ > 0.5, mean cos Δθ = ${meanCos.toFixed(2)}) toward ${activeTarget.value.directionDeg}°.`
})
</script>

<template>
  <section aria-labelledby="weather-correlation-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="weather-correlation-title" class="text-base font-semibold text-ink-primary">
            NASA POWER daily meteorology &amp; wind-fire alignment
          </h2>
          <span
            class="rounded-md border border-border-subtle bg-white/[0.04] px-2 py-0.5 text-[11px] font-medium text-ink-secondary"
          >
            <template v-if="activeTarget.fromCluster">
              Synced with Cluster #{{ activeTarget.clusterId }} ({{ activeTarget.directionDeg }}°)
            </template>
            <template v-else-if="activeTarget.fromPolygon">
              Drawn area centroid · {{ selectedYear }}
            </template>
            <template v-else>
              Reference point · {{ selectedYear }}
            </template>
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Combines NASA POWER daily 10 m wind vectors, 2 m temperature, relative humidity, and
          precipitation to measure cosine alignment (<code class="font-mono text-xs">cos Δθ</code>)
          with active fire spread.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup
          v-if="activeClusterContext"
          v-model="sourceMode"
          :options="SOURCE_OPTIONS"
          label="Coordinates source"
        />
        <BaseToggleGroup v-model="viewMode" :options="VIEW_OPTIONS" label="Weather chart mode" />
        <BaseToggleGroup
          v-if="!usingCluster"
          v-model="fireDirection"
          :options="DIRECTION_OPTIONS"
          label="Fire spread bearing"
        />
        <BaseSelect
          v-if="!usingCluster && !activeTarget.fromPolygon"
          v-model="presetLocation"
          :options="LOCATION_PRESETS"
          label="Reference location"
          :disabled="isLoading && correlationResult === null"
        />
      </div>
    </header>

    <div class="space-y-4 p-5">
      <div
        v-if="error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-100"
      >
        <span>Could not fetch NASA POWER weather data. {{ error }}</span>
        <button
          type="button"
          class="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-red-300/40 px-3 text-xs font-medium hover:bg-red-400/10 focus-visible:outline-2 focus-visible:outline-focus"
          @click="refresh"
        >
          <RotateCw aria-hidden="true" class="h-3.5 w-3.5" />
          Try again
        </button>
      </div>

      <BaseChartLoading
        v-if="correlationResult === null && isLoading"
        height-class="h-[21rem]"
        label="Loading weather correlation…"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No daily meteorological records returned for this point.
      </p>

      <template v-else-if="correlationResult !== null">
        <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoading">
          {{ summaryText }}
        </p>

        <div
          :class="
            isLoading
              ? 'opacity-60 transition-opacity duration-200'
              : 'transition-opacity duration-200'
          "
        >
          <WeatherCorrelationRenderer
            :correlation-rows="rows"
            :weather-rows="weatherRows"
            :mode="viewMode"
            :fire-direction-deg="activeTarget.directionDeg"
            :description="summaryText"
          />
        </div>

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          aria-label="Chart legend"
        >
          <template v-if="viewMode === 'alignment'">
            <li class="inline-flex items-center gap-2">
              <span class="h-3 w-3 rounded-sm bg-telemetry/60" />
              Wind speed WS10M (m/s)
            </li>
            <li class="inline-flex items-center gap-2">
              <span class="w-5 border-t-2 border-accent" />
              Wind-Fire alignment cos(Δθ) (+1 = tailwind, -1 = headwind)
            </li>
          </template>
          <template v-else>
            <li class="inline-flex items-center gap-2">
              <span class="w-5 border-t-2 border-accent" />
              Temperature T2M (°C)
            </li>
            <li class="inline-flex items-center gap-2">
              <span class="w-5 border-t-2 border-dashed border-telemetry" />
              Relative Humidity RH2M (%)
            </li>
            <li class="inline-flex items-center gap-2">
              <span class="h-3 w-3 rounded-sm bg-slate-400/50" />
              Precipitation (mm/day)
            </li>
          </template>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show daily wind-fire table ({{ rows.length }} days)</span>
            <span class="hidden group-open:inline">Hide daily wind-fire table</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[38rem] text-left text-xs tabular-nums">
              <thead class="border-b border-border-subtle text-ink-muted">
                <tr>
                  <th class="py-2 pr-3 font-medium">Date</th>
                  <th class="px-2 py-2 text-right font-medium">Wind (m/s)</th>
                  <th class="px-2 py-2 text-right font-medium">To (°)</th>
                  <th class="px-2 py-2 text-right font-medium">cos(Δθ)</th>
                  <th class="px-2 py-2 text-right font-medium">T2M (°C)</th>
                  <th class="pl-2 py-2 text-right font-medium">RH2M (%)</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="r in rows"
                  :key="r.date"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-1.5 pr-3 font-mono font-medium text-ink-primary">
                    {{ formatNasaDate(r.date) }}
                  </th>
                  <td class="px-2 py-1.5 text-right">{{ r.wind_speed?.toFixed(1) ?? '—' }}</td>
                  <td class="px-2 py-1.5 text-right">{{ r.wind_direction_to_deg?.toFixed(0) ?? '—' }}</td>
                  <td class="px-2 py-1.5 text-right text-accent-bright">
                    {{ r.wind_fire_alignment_cos?.toFixed(2) ?? '—' }}
                  </td>
                  <td class="px-2 py-1.5 text-right">{{ r.temperature?.toFixed(1) ?? '—' }}</td>
                  <td class="pl-2 py-1.5 text-right">{{ r.humidity?.toFixed(0) ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
