<script lang="ts">
export interface ActiveClusterContext {
  fireId: number
  latitude: number
  longitude: number
  startDate: string
  endDate: string
  directionDeg: number
}
</script>

<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { Compass, Play, RotateCw } from '@lucide/vue'
import { z } from 'zod'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useApiFetch } from '@/api/useApiFetch'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import ClusterMovementChart from '@/components/common/ClusterMovementChart.vue'
import PredictImportanceChart from '@/components/common/PredictImportanceChart.vue'

const props = defineProps<{
  polygon: GeoJSONPolygon | null
}>()

const selectedYear = defineModel<number>('year', { default: 2025 })
const clusterContext = defineModel<ActiveClusterContext | null>('clusterContext', {
  default: null,
})

const StepSchema = z.object({
  fire_id: z.number().int(),
  timestamp: z.string(),
  centroid_lat: z.number(),
  centroid_lon: z.number(),
  direction_deg: z.number().nullable(),
  cardinal_direction: z.string().nullable(),
  distance_km: z.number(),
  apparent_speed_kmh: z.number(),
  hotspot_count: z.number().int().nonnegative(),
  total_frp: z.number(),
  angle_change_deg: z.number().nullable(),
  direction_changed: z.boolean(),
  empty_intervals_before: z.number().int().nonnegative(),
})

const MovementResponseSchema = z.object({
  summary: z.object({
    hotspots_valid: z.number().int().nonnegative(),
    hotspots_dropped: z.number().int().nonnegative().optional(),
    clusters: z.number().int().nonnegative(),
    noise: z.number().int().nonnegative(),
  }),
  data: z.array(
    z.object({
      fire_id: z.number().int(),
      steps: z.array(StepSchema),
    }),
  ),
  total: z.number().int().nonnegative(),
})
type MovementResponse = z.infer<typeof MovementResponseSchema>

const PredictResponseSchema = z.object({
  metrics: z.object({
    train_samples: z.number().int(),
    test_samples: z.number().int(),
    mae_km: z.number(),
    rmse_km: z.number(),
    mae_east_km: z.number(),
    mae_north_km: z.number(),
    rmse_east_km: z.number(),
    rmse_north_km: z.number(),
    r2: z.number(),
    mean_angular_error_deg: z.number(),
    feature_importances: z.record(z.string(), z.number()),
    is_reliable: z.boolean(),
    reliability_note: z.string(),
  }),
  latest_prediction: z.object({
    predicted_east_km: z.number(),
    predicted_north_km: z.number(),
    predicted_distance_km: z.number(),
    predicted_direction_deg: z.number(),
    predicted_cardinal_direction: z.string(),
  }),
})
type PredictResponse = z.infer<typeof PredictResponseSchema>

const YEAR_OPTIONS = Array.from({ length: 26 }, (_, i) => {
  const y = 2026 - i
  return { value: y, label: String(y) }
})

const MONTH_OPTIONS = [
  { value: '03', label: 'March (1–15)' },
  { value: '04', label: 'April (1–15, Peak)' },
  { value: '05', label: 'May (1–15)' },
] as const

const EPS_OPTIONS = [
  { value: '1.5', label: '1.5 km' },
  { value: '3.0', label: '3.0 km' },
  { value: '5.0', label: '5.0 km' },
] as const

const selectedMonth = shallowRef<'03' | '04' | '05'>('04')
const epsKm = shallowRef<'1.5' | '3.0' | '5.0'>('3.0')
const selectedFireId = shallowRef<number>(0)

watch(
  selectedYear,
  (yr) => {
    if (yr === 2026 && selectedMonth.value !== '05') {
      selectedMonth.value = '05'
    }
  },
  { immediate: true },
)

const movementResult = shallowRef<MovementResponse | null>(null)
const isLoadingMovement = shallowRef(false)
const movementError = shallowRef<string | null>(null)
let latestMovementRequest = 0

const predictResult = shallowRef<PredictResponse | null>(null)
const isLoadingPredict = shallowRef(false)
const predictError = shallowRef<string | null>(null)

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

function buildPayload() {
  const yr = selectedYear.value
  const mo = yr === 2026 ? '05' : selectedMonth.value
  const startDate = `${yr}-${mo}-01T00:00:00`
  const endDate = `${yr}-${mo}-15T23:59:59`
  const bbox = polygonBbox(props.polygon)
  return {
    start_date: startDate,
    end_date: endDate,
    eps_km: Number(epsKm.value),
    min_samples: 3,
    time_window_hours: 24,
    max_time_window_hours: 96,
    interval_hours: 6,
    max_rows: 10000,
    ...(bbox
      ? {
          min_lat: bbox.minLat,
          max_lat: bbox.maxLat,
          min_lon: bbox.minLon,
          max_lon: bbox.maxLon,
        }
      : {}),
    ...(props.polygon ? { polygon: JSON.stringify(props.polygon) } : {}),
  }
}

async function loadMovement() {
  const requestId = ++latestMovementRequest
  isLoadingMovement.value = true
  movementError.value = null
  predictResult.value = null
  predictError.value = null

  const { data, error: fetchError } = await useApiFetch(
    '/analysis/cluster-movement?limit=50&offset=0',
  )
    .post(buildPayload())
    .json()

  if (requestId !== latestMovementRequest) return
  try {
    if (fetchError.value || !data.value) {
      throw fetchError.value ?? new Error('The server returned no data.')
    }
    const parsed = MovementResponseSchema.parse(data.value)
    // Priorizar clusters con varios intervalos temporales para visualizar movimiento real.
    parsed.data.sort((a, b) => b.steps.length - a.steps.length)
    movementResult.value = parsed
    selectedFireId.value = parsed.data[0]?.fire_id ?? 0
  } catch (err) {
    movementError.value = err instanceof Error ? err.message : 'Unknown error.'
  } finally {
    isLoadingMovement.value = false
  }
}

async function runPrediction() {
  isLoadingPredict.value = true
  predictError.value = null

  const payload = {
    ...buildPayload(),
    min_training_samples: 5,
    test_ratio: 0.2,
    n_estimators: 100,
  }

  const { data, error: fetchError } = await useApiFetch('/analysis/predict')
    .post(payload)
    .json()

  try {
    if (fetchError.value || !data.value) {
      throw fetchError.value ?? new Error('The server returned no prediction.')
    }
    predictResult.value = PredictResponseSchema.parse(data.value)
  } catch (err) {
    predictError.value = err instanceof Error ? err.message : 'Unknown error.'
  } finally {
    isLoadingPredict.value = false
  }
}

watch([selectedYear, selectedMonth, epsKm, () => props.polygon], loadMovement, { immediate: true })

const fires = computed(() => movementResult.value?.data ?? [])
const fireOptions = computed(() =>
  fires.value.slice(0, 25).map((f) => ({
    value: f.fire_id,
    label: `Cluster #${f.fire_id} (${f.steps.length} steps)`,
  })),
)
const activeFire = computed(
  () => fires.value.find((f) => f.fire_id === selectedFireId.value) ?? fires.value[0] ?? null,
)

watch(
  activeFire,
  (fire) => {
    if (!fire || fire.steps.length === 0) {
      clusterContext.value = null
      return
    }
    const n = fire.steps.length
    const meanLat = fire.steps.reduce((s, step) => s + step.centroid_lat, 0) / n
    const meanLon = fire.steps.reduce((s, step) => s + step.centroid_lon, 0) / n
    const stepWithDir = [...fire.steps].reverse().find((s) => s.direction_deg !== null)
    const directionDeg = Math.round(stepWithDir?.direction_deg ?? 270)
    const yr = selectedYear.value
    const mo = yr === 2026 ? '05' : selectedMonth.value
    clusterContext.value = {
      fireId: fire.fire_id,
      latitude: Number(meanLat.toFixed(4)),
      longitude: Number(meanLon.toFixed(4)),
      startDate: `${yr}-${mo}-01T00:00:00`,
      endDate: `${yr}-${mo}-15T23:59:59`,
      directionDeg,
    }
  },
  { immediate: true },
)

const summaryText = computed(() => {
  if (!movementResult.value) return ''
  const s = movementResult.value.summary
  return `Clustered ${s.hotspots_valid.toLocaleString()} detections into ${s.clusters.toLocaleString()} spatio-temporal fire clusters (${s.noise.toLocaleString()} isolated noise points) using Haversine DBSCAN (eps = ${epsKm.value} km).`
})
</script>

<template>
  <section aria-labelledby="cluster-movement-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="cluster-movement-title" class="text-base font-semibold text-ink-primary">
            Spatio-temporal cluster movement &amp; RandomForest prediction
          </h2>
          <span
            class="rounded-md border border-border-subtle bg-white/[0.04] px-2 py-0.5 text-[11px] font-medium text-ink-secondary"
          >
            {{ polygon ? 'Drawn area (Polygon)' : 'All regions' }} · Spatio-temporal DBSCAN
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Clusters hotspots in space and time (<code class="font-mono text-xs">/analysis/cluster-movement</code>)
          to track centroid displacement per 6-hour interval, and trains a RandomForest regressor
          with NASA POWER meteorology (<code class="font-mono text-xs">/analysis/predict</code>).
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup v-model="epsKm" :options="EPS_OPTIONS" label="DBSCAN radius (km)" />
        <BaseSelect
          v-model="selectedMonth"
          :options="MONTH_OPTIONS"
          label="Window"
          :disabled="(isLoadingMovement && movementResult === null) || selectedYear === 2026"
        />
        <BaseSelect
          v-model="selectedYear"
          :options="YEAR_OPTIONS"
          label="Year"
          :disabled="isLoadingMovement && movementResult === null"
        />
      </div>
    </header>

    <div class="space-y-6 p-5">
      <div
        v-if="movementError"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-100"
      >
        <span>Could not analyze cluster movement. {{ movementError }}</span>
        <button
          type="button"
          class="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-red-300/40 px-3 text-xs font-medium hover:bg-red-400/10 focus-visible:outline-2 focus-visible:outline-focus"
          @click="loadMovement"
        >
          <RotateCw aria-hidden="true" class="h-3.5 w-3.5" />
          Try again
        </button>
      </div>

      <div
        v-if="movementResult === null && isLoadingMovement"
        class="h-[20rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
      />

      <p
        v-else-if="movementResult !== null && fires.length === 0"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No multi-point fire clusters formed in this window and area. Try increasing the DBSCAN
        radius or switching the sample window.
      </p>

      <template v-else-if="movementResult !== null && activeFire !== null">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoadingMovement">
            {{ summaryText }}
          </p>
          <BaseSelect
            v-if="fireOptions.length > 0"
            v-model="selectedFireId"
            :options="fireOptions"
            label="Select fire cluster"
          />
        </div>

        <div
          :class="
            isLoadingMovement
              ? 'opacity-60 transition-opacity duration-200'
              : 'transition-opacity duration-200'
          "
        >
          <ClusterMovementChart
            :steps="activeFire.steps"
            :fire-id="activeFire.fire_id"
            :description="`Interval displacement and speed chart for fire cluster ${activeFire.fire_id}`"
          />
        </div>

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          aria-label="Chart legend"
        >
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm bg-telemetry/60" />
            Step distance (km)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-2 border-accent" />
            Apparent speed (km/h)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-2 border-dashed border-accent-bright" />
            Total FRP (MW)
          </li>
        </ul>

        <div class="rounded-xl border border-border-subtle bg-surface-base/40 p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold text-ink-primary">
                RandomForest displacement predictor (<code class="font-mono text-xs text-ink-secondary">POST /analysis/predict</code>)
              </h3>
              <p class="mt-1 text-xs text-ink-muted">
                Joins cluster trajectories with NASA POWER daily wind and humidity to predict the
                next displacement vector (east/north km) and rank predictor importance.
              </p>
            </div>
            <button
              type="button"
              :disabled="isLoadingPredict"
              class="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-accent/40 bg-accent/15 px-3.5 text-xs font-medium text-accent-bright transition-colors hover:bg-accent/25 focus-visible:outline-2 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-50"
              @click="runPrediction"
            >
              <Play aria-hidden="true" class="h-3.5 w-3.5" />
              {{ isLoadingPredict ? 'Training model…' : 'Run RandomForest predictor' }}
            </button>
          </div>

          <div
            v-if="predictError"
            role="alert"
            class="mt-4 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-xs text-red-100"
          >
            {{ predictError }}
          </div>

          <div
            v-if="isLoadingPredict && !predictResult"
            class="mt-4 h-[15rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
            aria-hidden="true"
          />

          <div v-else-if="predictResult" class="mt-4 space-y-4">
            <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
                <p class="text-[11px] text-ink-muted">Predicted Vector</p>
                <p class="mt-1 inline-flex items-center gap-1.5 font-mono text-base font-semibold text-accent-bright">
                  <Compass aria-hidden="true" class="h-4 w-4" />
                  {{ predictResult.latest_prediction.predicted_distance_km.toFixed(2) }} km
                  {{ predictResult.latest_prediction.predicted_cardinal_direction }}
                  ({{ predictResult.latest_prediction.predicted_direction_deg.toFixed(0) }}°)
                </p>
              </div>
              <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
                <p class="text-[11px] text-ink-muted">Spatial MAE / RMSE</p>
                <p class="mt-1 font-mono text-base font-semibold text-ink-primary">
                  {{ predictResult.metrics.mae_km.toFixed(2) }} /
                  {{ predictResult.metrics.rmse_km.toFixed(2) }} km
                </p>
              </div>
              <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
                <p class="text-[11px] text-ink-muted">Angular Error</p>
                <p class="mt-1 font-mono text-base font-semibold text-ink-primary">
                  {{ predictResult.metrics.mean_angular_error_deg.toFixed(1) }}°
                </p>
              </div>
              <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
                <p class="text-[11px] text-ink-muted">Train / Test Split</p>
                <p class="mt-1 font-mono text-base font-semibold text-ink-primary">
                  {{ predictResult.metrics.train_samples }} /
                  {{ predictResult.metrics.test_samples }} steps
                </p>
              </div>
            </div>

            <p class="text-xs text-ink-muted">
              {{ predictResult.metrics.reliability_note }} (R² =
              {{ predictResult.metrics.r2.toFixed(3) }}).
            </p>

            <PredictImportanceChart
              :importances="predictResult.metrics.feature_importances"
              description="RandomForest feature importance percentages for fire displacement prediction"
            />
          </div>
        </div>
      </template>
    </div>
  </section>
</template>
