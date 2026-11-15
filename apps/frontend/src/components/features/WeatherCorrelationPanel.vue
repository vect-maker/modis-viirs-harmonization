<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useApiFetch } from '@/api/useApiFetch'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import WeatherCorrelationChart, {
  formatNasaDate,
  type RawWeatherRecord,
} from '@/components/common/WeatherCorrelationChart.vue'
import type { ActiveClusterContext } from './ClusterMovementPanel.vue'

const props = defineProps<{
  polygon: GeoJSONPolygon | null
  clusterContext?: ActiveClusterContext | null
}>()

const selectedYear = defineModel<number>('year', { default: 2025 })

const CorrelationRecordSchema = z.object({
  date: z.string(),
  is_complete: z.boolean(),
  wind_speed: z.number().nullable(),
  wind_direction_from_deg: z.number().nullable(),
  wind_direction_to_deg: z.number().nullable(),
  wind_u: z.number().nullable(),
  wind_v: z.number().nullable(),
  temperature: z.number().nullable(),
  humidity: z.number().nullable(),
  precipitation: z.number().nullable(),
  wind_fire_angle_diff_deg: z.number().nullable(),
  wind_fire_alignment_cos: z.number().nullable(),
  status_message: z.string(),
})

const CorrelationResponseSchema = z.object({
  data: z.array(CorrelationRecordSchema),
  total: z.number().int().nonnegative(),
})
type CorrelationResponse = z.infer<typeof CorrelationResponseSchema>

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

const correlationResult = shallowRef<CorrelationResponse | null>(null)
const weatherRows = shallowRef<readonly RawWeatherRecord[]>([])
const isLoading = shallowRef(false)
const error = shallowRef<string | null>(null)
let latestRequest = 0

const usingCluster = computed(
  () => sourceMode.value === 'cluster' && props.clusterContext != null,
)

const activeTarget = computed(() => {
  if (usingCluster.value && props.clusterContext) {
    return {
      latitude: props.clusterContext.latitude,
      longitude: props.clusterContext.longitude,
      startDate: props.clusterContext.startDate,
      endDate: props.clusterContext.endDate,
      directionDeg: props.clusterContext.directionDeg,
      fromPolygon: false,
      fromCluster: true,
      clusterId: props.clusterContext.fireId,
    }
  }
  const yr = selectedYear.value
  const mo = yr === 2026 ? '05' : '04'
  const startDate = `${yr}-${mo}-01T00:00:00`
  const endDate = `${yr}-${mo}-15T23:59:59`

  if (props.polygon) {
    const ring = props.polygon.coordinates[0]
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

async function load() {
  const requestId = ++latestRequest
  isLoading.value = true
  error.value = null

  const { latitude, longitude, startDate, endDate, directionDeg } = activeTarget.value

  const [corrFetch, rawFetch] = await Promise.all([
    useApiFetch('/analysis/weather-correlation?limit=50&offset=0')
      .post({
        latitude,
        longitude,
        start_date: startDate,
        end_date: endDate,
        fire_direction_deg: directionDeg,
      })
      .json(),
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

  if (requestId !== latestRequest) return
  try {
    if (corrFetch.error.value || !corrFetch.data.value) {
      throw corrFetch.error.value ?? new Error('Could not query NASA POWER weather correlation.')
    }
    correlationResult.value = CorrelationResponseSchema.parse(corrFetch.data.value)
    if (rawFetch.data.value) {
      const parsedRaw = RawWeatherResponseSchema.safeParse(rawFetch.data.value)
      weatherRows.value = parsedRaw.success ? parsedRaw.data.data : []
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error.'
  } finally {
    isLoading.value = false
  }
}

watch(
  [
    presetLocation,
    fireDirection,
    sourceMode,
    selectedYear,
    () => props.polygon,
    () => props.clusterContext,
  ],
  load,
  { immediate: true },
)

const rows = computed(() => correlationResult.value?.data ?? [])
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
          Queries NASA POWER (<code class="font-mono text-xs">/weather</code> &amp;
          <code class="font-mono text-xs">/analysis/weather-correlation</code>) for 10 m wind
          vectors, 2 m temperature, relative humidity, and precipitation, measuring cosine
          alignment (<code class="font-mono text-xs">cos Δθ</code>) with fire spread direction.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup
          v-if="clusterContext"
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
          @click="load"
        >
          <RotateCw aria-hidden="true" class="h-3.5 w-3.5" />
          Try again
        </button>
      </div>

      <div
        v-if="correlationResult === null && isLoading"
        class="h-[21rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
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
          <WeatherCorrelationChart
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
              Precipitation PRECTOTCORR (mm/day)
            </li>
          </template>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show daily NASA POWER records ({{ rows.length }})</span>
            <span class="hidden group-open:inline">Hide daily NASA POWER records</span>
          </summary>
          <div class="max-h-72 overflow-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[38rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Daily meteorological and wind vector alignment table
              </caption>
              <thead class="sticky top-0 bg-surface-panel text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Date</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Wind (m/s)</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Wind To (°)</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">cos(Δθ)</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Temp (°C)</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Humidity (%)</th>
                  <th scope="col" class="py-2 text-right font-medium">Precip (mm)</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="row in rows"
                  :key="row.date"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-mono font-medium text-ink-primary">
                    {{ formatNasaDate(row.date) }}
                  </th>
                  <td class="py-2 pr-4 text-right">{{ row.wind_speed?.toFixed(1) ?? '—' }}</td>
                  <td class="py-2 pr-4 text-right">
                    {{ row.wind_direction_to_deg !== null ? `${row.wind_direction_to_deg.toFixed(0)}°` : '—' }}
                  </td>
                  <td class="py-2 pr-4 text-right font-mono text-accent-bright">
                    {{ row.wind_fire_alignment_cos?.toFixed(3) ?? '—' }}
                  </td>
                  <td class="py-2 pr-4 text-right">{{ row.temperature?.toFixed(1) ?? '—' }}</td>
                  <td class="py-2 pr-4 text-right">{{ row.humidity?.toFixed(1) ?? '—' }}</td>
                  <td class="py-2 text-right">{{ row.precipitation?.toFixed(2) ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
