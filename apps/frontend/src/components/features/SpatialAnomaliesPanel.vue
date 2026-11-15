<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useApiFetch } from '@/api/useApiFetch'
import { ChartResponseSchema } from '@/api/modules/shared/schemas'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import SpatialAnomaliesChart from '@/components/common/SpatialAnomaliesChart.vue'

const props = defineProps<{
  polygon: GeoJSONPolygon | null
}>()

const selectedYear = defineModel<number>('year', { default: 2025 })

const ResponseSchema = z.object({
  summary: z.object({
    total_points: z.number().int().nonnegative(),
    normal_count: z.number().int().nonnegative(),
    anomaly_count: z.number().int().nonnegative(),
    anomaly_pct: z.number(),
    returned_points: z.number().int().nonnegative().optional(),
  }),
  points: z.array(
    z.object({
      id: z.string(),
      latitude: z.number(),
      longitude: z.number(),
      frp: z.number().nullable(),
      acq_datetime: z.string(),
      anomaly: z.number().int(),
      is_anomaly: z.boolean(),
      score: z.number(),
    }),
  ),
})
type SpatialAnomaliesResponse = z.infer<typeof ResponseSchema>

const MODE_OPTIONS = [
  { value: 'geo', label: 'Lon vs. Lat' },
  { value: 'score', label: 'Score vs. FRP' },
] as const

const CONTAMINATION_OPTIONS = [
  { value: 'auto', label: 'Auto' },
  { value: '0.05', label: '5% outliers' },
  { value: '0.1', label: '10% outliers' },
] as const

const MONTH_OPTIONS = [
  { value: '04', label: 'Apr (Peak)' },
  { value: '05', label: 'May' },
  { value: '03', label: 'Mar' },
  { value: '02', label: 'Feb' },
  { value: '01', label: 'Jan' },
  { value: 'all', label: 'Full year' },
] as const

const YEAR_OPTIONS = Array.from({ length: 26 }, (_, idx) => {
  const year = 2026 - idx
  return { value: year, label: String(year) }
})

const MAX_ROWS = 25000
const plotMode = shallowRef<'geo' | 'score'>('geo')
const contamination = shallowRef<'auto' | '0.05' | '0.1'>('auto')
const selectedMonth = shallowRef<string>('04')
const result = shallowRef<SpatialAnomaliesResponse | null>(null)
const isLoading = shallowRef(false)
const error = shallowRef<string | null>(null)
let latestRequest = 0

function polygonBbox(polygon: GeoJSONPolygon | null) {
  if (!polygon) return null
  const ring = polygon.coordinates[0]
  if (!ring || ring.length === 0) return null
  let minLon = Infinity
  let maxLon = -Infinity
  let minLat = Infinity
  let maxLat = -Infinity
  for (const pt of ring) {
    const lon = pt[0]
    const lat = pt[1]
    if (lon === undefined || lat === undefined) continue
    if (lon < minLon) minLon = lon
    if (lon > maxLon) maxLon = lon
    if (lat < minLat) minLat = lat
    if (lat > maxLat) maxLat = lat
  }
  return Number.isFinite(minLat) ? { minLat, maxLat, minLon, maxLon } : null
}

function resolveDateBounds(year: number, month: string): { start: string; end: string } {
  if (month === 'all') {
    return {
      start: `${year}-01-01T00:00:00`,
      end: `${year}-12-31T23:59:59`,
    }
  }
  const mNum = Number(month)
  const lastDay = new Date(Date.UTC(year, mNum, 0)).getUTCDate()
  return {
    start: `${year}-${month}-01`,
    end: `${year}-${month}-${String(lastDay).padStart(2, '0')}`,
  }
}

async function load() {
  const requestId = ++latestRequest
  isLoading.value = true
  error.value = null

  const bounds = resolveDateBounds(selectedYear.value, selectedMonth.value)
  const params = new URLSearchParams({
    n_estimators: '150',
    max_rows: String(MAX_ROWS),
    max_points_returned: '3000',
    start_date: bounds.start,
    end_date: bounds.end,
  })
  if (contamination.value !== 'auto') {
    params.set('contamination', contamination.value)
  }
  const bbox = polygonBbox(props.polygon)
  if (bbox) {
    params.set('min_lat', String(bbox.minLat))
    params.set('max_lat', String(bbox.maxLat))
    params.set('min_lon', String(bbox.minLon))
    params.set('max_lon', String(bbox.maxLon))
  }
  if (props.polygon) {
    params.set('polygon', JSON.stringify(props.polygon))
  }

  const { data, error: fetchError } = await useApiFetch(
    `/charts/diagnostics/spatial-anomalies?${params.toString()}`,
  )
    .get()
    .json()

  if (requestId !== latestRequest) return
  try {
    if (fetchError.value || !data.value) {
      throw fetchError.value ?? new Error('The server returned no data.')
    }
    result.value = ChartResponseSchema(ResponseSchema).parse(data.value).data
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error.'
  } finally {
    isLoading.value = false
  }
}

watch([contamination, selectedYear, selectedMonth, () => props.polygon], load, { immediate: true })

const points = computed(() => result.value?.points ?? [])
const topAnomalies = computed(() =>
  points.value
    .filter((p) => p.is_anomaly)
    .sort((a, b) => a.score - b.score)
    .slice(0, 20),
)
const isEmpty = computed(
  () => result.value !== null && result.value.summary.total_points === 0,
)
const hitRowCap = computed(
  () => (result.value?.summary.total_points ?? 0) >= MAX_ROWS,
)
const pctFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })

const summaryText = computed(() => {
  if (!result.value) return ''
  const s = result.value.summary
  return `Evaluated ${s.total_points.toLocaleString()} points with IsolationForest: ${s.anomaly_count.toLocaleString()} spatial outliers (${pctFmt.format(s.anomaly_pct)}%) and ${s.normal_count.toLocaleString()} normal points.`
})

const chartDescription = computed(
  () => `IsolationForest spatial anomaly scatter plot. ${summaryText.value}`,
)
</script>

<template>
  <section aria-labelledby="spatial-anomalies-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="spatial-anomalies-title" class="text-base font-semibold text-ink-primary">
            Spatial outlier detection (IsolationForest)
          </h2>
          <span
            class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 text-[11px] text-ink-muted"
          >
            {{ polygon ? 'Drawn area (Polygon)' : 'All regions' }} · Uniform sample
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Fits an IsolationForest ensemble on coordinates to flag isolated hotspots far from main
          burning corridors. Select a month to evaluate all points without hitting the SQL row cap.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup v-model="plotMode" :options="MODE_OPTIONS" label="Plot axes" />
        <BaseToggleGroup
          v-model="contamination"
          :options="CONTAMINATION_OPTIONS"
          label="Contamination threshold"
        />
        <BaseSelect
          v-model="selectedMonth"
          :options="MONTH_OPTIONS"
          label="Sample month"
          :disabled="isLoading && result === null"
        />
        <BaseSelect
          v-model="selectedYear"
          :options="YEAR_OPTIONS"
          label="Sample year"
          :disabled="isLoading && result === null"
        />
      </div>
    </header>

    <div class="space-y-4 p-5">
      <div
        v-if="error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-100"
      >
        <span>Could not load spatial anomalies. {{ error }}</span>
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
        v-if="result === null && isLoading"
        class="h-[32rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse sm:h-[38rem] lg:h-[42rem]"
        aria-hidden="true"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No hotspot coordinates available for this selection.
      </p>

      <template v-else-if="result !== null">
        <p
          v-if="hitRowCap"
          class="rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 text-xs leading-relaxed text-accent-bright"
        >
          Sampled {{ MAX_ROWS.toLocaleString() }} uniformly distributed rows across the period. Pick
          a single month or draw an area on the map to evaluate 100% of detections in that window.
        </p>

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
          <SpatialAnomaliesChart
            :points="points"
            :mode="plotMode"
            :description="chartDescription"
          />
        </div>

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          aria-label="Chart legend"
        >
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm border border-accent-bright bg-accent" />
            Spatial anomaly (IsolationForest -1)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm bg-slate-500/60" />
            Normal cluster point (+1)
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show top 20 strongest spatial outliers</span>
            <span class="hidden group-open:inline">Hide top 20 strongest spatial outliers</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[36rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Strongest spatial anomaly detections ranked by IsolationForest score
              </caption>
              <thead class="text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Timestamp (UTC)</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Latitude</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Longitude</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">FRP</th>
                  <th scope="col" class="py-2 text-right font-medium">Decision Score</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="pt in topAnomalies"
                  :key="pt.id"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-mono font-medium text-ink-primary">
                    {{ pt.acq_datetime.slice(0, 19) }}
                  </th>
                  <td class="py-2 pr-4 text-right font-mono">{{ pt.latitude.toFixed(4) }}°</td>
                  <td class="py-2 pr-4 text-right font-mono">{{ pt.longitude.toFixed(4) }}°</td>
                  <td class="py-2 pr-4 text-right">
                    {{ pt.frp !== null ? `${pt.frp.toFixed(1)} MW` : '—' }}
                  </td>
                  <td class="py-2 text-right font-mono text-accent-bright">
                    {{ pt.score.toFixed(4) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
