<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Compass, Play, RotateCw } from '@lucide/vue'
import { polygonBbox, useModelChartsApi, type FirePredictData } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useChartFiltersStore } from '@/stores/chartFilters'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import ClusterMovementRenderer from '@/components/common/ClusterMovementChart.vue'
import PredictImportanceChart from '@/components/common/PredictImportanceChart.vue'

const filtersStore = useChartFiltersStore()
const { activePolygon, selectedYear: storeYear } = storeToRefs(filtersStore)
const { getClusterMovement, getPredict } = useModelChartsApi()

const selectedYear = computed<number>({
  get: () => storeYear.value,
  set: (value) => filtersStore.setSelectedYear(value),
})

const EPS_OPTIONS = [
  { value: '1', label: '1 km' },
  { value: '2', label: '2 km' },
  { value: '5', label: '5 km' },
] as const

const MONTH_OPTIONS = [
  { value: '04', label: 'April (Peak)' },
  { value: '03', label: 'March' },
  { value: '05', label: 'May' },
  { value: '02', label: 'February' },
] as const

const YEAR_OPTIONS = Array.from({ length: 26 }, (_, idx) => {
  const year = 2026 - idx
  return { value: year, label: String(year) }
})

const epsKm = shallowRef<'1' | '2' | '5'>('2')
const selectedMonth = shallowRef<'02' | '03' | '04' | '05'>('04')
const selectedFireId = shallowRef<number>(0)

const predictResult = shallowRef<FirePredictData | null>(null)
const isLoadingPredict = shallowRef(false)
const predictError = shallowRef<string | null>(null)

function buildQueryParams() {
  const yr = selectedYear.value
  const mo = yr === 2026 ? '05' : selectedMonth.value
  const bbox = polygonBbox(activePolygon.value)
  return {
    start_date: `${yr}-${mo}-01`,
    end_date: `${yr}-${mo}-15`,
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
    polygon: activePolygon.value,
  }
}

const {
  data: movementResult,
  isLoading: isLoadingMovement,
  error: movementError,
  refresh: refreshMovement,
} = useChartLifecycle({
  fetcher: async () => {
    predictResult.value = null
    predictError.value = null
    const parsed = await getClusterMovement({
      ...buildQueryParams(),
      limit: 50,
      offset: 0,
    })
    const sortedFires = [...parsed.fires].sort((a, b) => b.steps.length - a.steps.length)
    selectedFireId.value = sortedFires[0]?.fire_id ?? 0
    return { ...parsed, fires: sortedFires }
  },
  watchSources: [selectedYear, selectedMonth, epsKm, activePolygon],
})

async function runPrediction() {
  isLoadingPredict.value = true
  predictError.value = null
  try {
    predictResult.value = await getPredict({
      ...buildQueryParams(),
      min_training_samples: 5,
      test_ratio: 0.2,
      n_estimators: 100,
    })
  } catch (err) {
    predictError.value = err instanceof Error ? err.message : 'Unknown error.'
  } finally {
    isLoadingPredict.value = false
  }
}

const fires = computed(() => movementResult.value?.fires ?? [])
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
      filtersStore.setActiveClusterContext(null)
      return
    }
    const n = fire.steps.length
    const meanLat = fire.steps.reduce((s, step) => s + step.centroid_lat, 0) / n
    const meanLon = fire.steps.reduce((s, step) => s + step.centroid_lon, 0) / n
    const stepWithDir = [...fire.steps].reverse().find((s) => s.direction_deg !== null)
    const directionDeg = Math.round(stepWithDir?.direction_deg ?? 270)
    const yr = selectedYear.value
    const mo = yr === 2026 ? '05' : selectedMonth.value
    filtersStore.setActiveClusterContext({
      fireId: fire.fire_id,
      latitude: Number(meanLat.toFixed(4)),
      longitude: Number(meanLon.toFixed(4)),
      startDate: `${yr}-${mo}-01T00:00:00`,
      endDate: `${yr}-${mo}-15T23:59:59`,
      directionDeg,
    })
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
            {{ activePolygon ? 'Drawn area (Polygon)' : 'All regions' }} · Spatio-temporal DBSCAN
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Clusters hotspots in space and time (<code class="font-mono text-xs">/charts/models/cluster-movement</code>)
          to track centroid displacement per 6-hour interval, and trains a RandomForest regressor
          with NASA POWER meteorology (<code class="font-mono text-xs">/charts/models/predict</code>).
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup v-model="epsKm" :options="EPS_OPTIONS" label="DBSCAN radius (km)" />
        <BaseSelect
          v-model="selectedMonth"
          :options="MONTH_OPTIONS"
          label="Month window"
          :disabled="isLoadingMovement && movementResult === null"
        />
        <BaseSelect
          v-model="selectedYear"
          :options="YEAR_OPTIONS"
          label="Year"
          :disabled="isLoadingMovement && movementResult === null"
        />
      </div>
    </header>

    <div class="space-y-5 p-5">
      <div
        v-if="movementError"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-100"
      >
        <span>Could not load cluster movement. {{ movementError }}</span>
        <button
          type="button"
          class="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-red-300/40 px-3 text-xs font-medium hover:bg-red-400/10 focus-visible:outline-2 focus-visible:outline-focus"
          @click="refreshMovement"
        >
          <RotateCw aria-hidden="true" class="h-3.5 w-3.5" />
          Try again
        </button>
      </div>

      <div
        v-if="movementResult === null && isLoadingMovement"
        class="h-[21rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
      />

      <p
        v-else-if="movementResult !== null && fires.length === 0"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No multi-hotspot clusters formed in this 15-day window. Try a larger radius or another month.
      </p>

      <template v-else-if="movementResult !== null">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoadingMovement">
            {{ summaryText }}
          </p>
          <BaseSelect
            v-if="fireOptions.length > 0"
            v-model="selectedFireId"
            :options="fireOptions"
            label="Inspect cluster"
          />
        </div>

        <div
          v-if="activeFire"
          :class="
            isLoadingMovement
              ? 'opacity-60 transition-opacity duration-200'
              : 'transition-opacity duration-200'
          "
        >
          <ClusterMovementRenderer
            :steps="activeFire.steps"
            :fire-id="activeFire.fire_id"
            :description="`Centroid trajectory for Fire Cluster #${activeFire.fire_id}`"
          />
        </div>

        <div class="rounded-xl border border-border-subtle bg-white/[0.03] p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold text-ink-primary">
                RandomForest displacement predictor (<code class="font-mono text-xs text-ink-secondary">GET /charts/models/predict</code>)
              </h3>
              <p class="mt-0.5 text-xs text-ink-muted">
                Trains on spatio-temporal trajectory steps joined with NASA POWER wind &amp; weather vectors.
              </p>
            </div>
            <button
              type="button"
              :disabled="isLoadingPredict"
              class="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-accent/40 bg-accent/15 px-3.5 text-xs font-medium text-accent-bright transition hover:bg-accent/25 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-focus"
              @click="runPrediction"
            >
              <Play aria-hidden="true" class="h-3.5 w-3.5" />
              {{ isLoadingPredict ? 'Training RandomForest…' : 'Train & predict displacement' }}
            </button>
          </div>

          <p v-if="predictError" class="mt-3 text-xs text-red-200">
            {{ predictError }}
          </p>

          <div v-if="predictResult" class="mt-4 space-y-4">
            <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div class="rounded-lg border border-border-subtle bg-surface-panel p-3">
                <p class="text-[11px] text-ink-muted">Next step distance</p>
                <p class="mt-1 font-mono text-base font-semibold text-accent-bright tabular-nums">
                  {{ predictResult.latest_prediction.predicted_distance_km.toFixed(2) }} km
                </p>
              </div>
              <div class="rounded-lg border border-border-subtle bg-surface-panel p-3">
                <p class="text-[11px] text-ink-muted">Predicted bearing</p>
                <p class="mt-1 inline-flex items-center gap-1.5 font-mono text-base font-semibold text-ink-primary">
                  <Compass aria-hidden="true" class="h-4 w-4 text-accent-bright" />
                  {{ predictResult.latest_prediction.predicted_direction_deg.toFixed(0) }}°
                  ({{ predictResult.latest_prediction.predicted_cardinal_direction }})
                </p>
              </div>
              <div class="rounded-lg border border-border-subtle bg-surface-panel p-3">
                <p class="text-[11px] text-ink-muted">Mean distance error</p>
                <p class="mt-1 font-mono text-base font-semibold text-ink-primary tabular-nums">
                  {{ predictResult.metrics.mean_distance_error_km.toFixed(2) }} km
                </p>
              </div>
              <div class="rounded-lg border border-border-subtle bg-surface-panel p-3">
                <p class="text-[11px] text-ink-muted">Train / Test samples</p>
                <p class="mt-1 font-mono text-base font-semibold text-ink-primary tabular-nums">
                  {{ predictResult.metrics.train_samples }} / {{ predictResult.metrics.test_samples }}
                </p>
              </div>
            </div>

            <PredictImportanceChart
              :importances="predictResult.metrics.feature_importances"
              description="RandomForest feature importance ranking for fire displacement prediction"
            />
          </div>
        </div>
      </template>
    </div>
  </section>
</template>
