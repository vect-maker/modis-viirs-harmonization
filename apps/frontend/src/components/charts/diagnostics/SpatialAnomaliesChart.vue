<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { polygonBbox, useDiagnosticChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useChartFiltersStore } from '@/stores/chartFilters'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import SpatialAnomaliesRenderer from '@/components/common/SpatialAnomaliesChart.vue'

const filtersStore = useChartFiltersStore()
const { activePolygon, selectedYear: storeYear } = storeToRefs(filtersStore)
const { getSpatialAnomalies } = useDiagnosticChartsApi()

const selectedYear = computed<number>({
  get: () => storeYear.value,
  set: (value) => filtersStore.setSelectedYear(value),
})

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

function resolveDateBounds(year: number, month: string): { start: string; end: string } {
  if (month === 'all') {
    return {
      start: `${year}-01-01`,
      end: `${year}-12-31`,
    }
  }
  const m = Number(month)
  const lastDay = new Date(Date.UTC(year, m, 0)).getUTCDate()
  return {
    start: `${year}-${month}-01`,
    end: `${year}-${month}-${String(lastDay).padStart(2, '0')}`,
  }
}

const {
  data: result,
  isLoading,
  error,
  refresh,
} = useChartLifecycle({
  fetcher: () => {
    const bounds = resolveDateBounds(selectedYear.value, selectedMonth.value)
    const bbox = polygonBbox(activePolygon.value)
    return getSpatialAnomalies({
      n_estimators: 150,
      max_rows: MAX_ROWS,
      max_points_returned: 3000,
      start_date: bounds.start,
      end_date: bounds.end,
      contamination: contamination.value !== 'auto' ? contamination.value : undefined,
      ...(bbox
        ? {
            min_lat: bbox.minLat,
            max_lat: bbox.maxLat,
            min_lon: bbox.minLon,
            max_lon: bbox.maxLon,
          }
        : {}),
      polygon: activePolygon.value,
    })
  },
  watchSources: [contamination, selectedYear, selectedMonth, activePolygon],
})

const points = computed(() =>
  (result.value?.points ?? []).map((p) => ({
    ...p,
    acq_datetime: p.acq_datetime ?? '',
  })),
)
const topAnomalies = computed(() =>
  points.value
    .filter((p) => p.is_anomaly)
    .slice(0, 20),
)
const isEmpty = computed(() => result.value !== null && points.value.length === 0)
const pctFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })

const periodLabel = computed(() => {
  const m = MONTH_OPTIONS.find((opt) => opt.value === selectedMonth.value)?.label ?? selectedMonth.value
  return selectedMonth.value === 'all' ? String(selectedYear.value) : `${m} ${selectedYear.value}`
})

const summaryText = computed(() => {
  if (!result.value) return ''
  const s = result.value.summary
  const sampleNote =
    s.total_points >= MAX_ROWS
      ? ` (sampled up to ${MAX_ROWS.toLocaleString()} rows)`
      : ''
  return `In ${periodLabel.value}, IsolationForest evaluated ${s.total_points.toLocaleString()} detections${sampleNote} and flagged ${s.anomaly_count.toLocaleString()} spatial anomalies (${pctFmt.format(s.anomaly_pct)}%).`
})

const chartDescription = computed(
  () => `IsolationForest spatial anomaly scatter plot for ${periodLabel.value}. ${summaryText.value}`,
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
            {{ activePolygon ? 'Drawn area (Polygon)' : 'All regions' }} · 150 trees
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Detects geographically isolated hotspots that fall outside dense regional fire clusters
          using scikit-learn IsolationForest.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup
          v-model="plotMode"
          :options="[
            { value: 'geo', label: 'Lat / Lon' },
            { value: 'score', label: 'Anomaly Score' },
          ]"
          label="Plot axes"
        />
        <BaseToggleGroup
          v-model="contamination"
          :options="CONTAMINATION_OPTIONS"
          label="Contamination"
        />
        <BaseSelect
          v-model="selectedMonth"
          :options="MONTH_OPTIONS"
          label="Month"
          :disabled="isLoading && result === null"
        />
        <BaseSelect
          v-model="selectedYear"
          :options="YEAR_OPTIONS"
          label="Year"
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
          @click="refresh"
        >
          <RotateCw aria-hidden="true" class="h-3.5 w-3.5" />
          Try again
        </button>
      </div>

      <div
        v-if="result === null && isLoading"
        class="h-[22rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No hotspot coordinates available for {{ periodLabel }}.
      </p>

      <template v-else-if="result !== null">
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
          <SpatialAnomaliesRenderer
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
            <span class="h-3 w-3 rounded-full bg-telemetry/60" />
            Normal cluster point
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-full bg-accent-bright" />
            Isolated spatial anomaly (score &lt; 0)
          </li>
        </ul>

        <details v-if="topAnomalies.length > 0" class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show top 20 spatial anomalies</span>
            <span class="hidden group-open:inline">Hide spatial anomalies table</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[34rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Top 20 spatial anomalies detected by IsolationForest
              </caption>
              <thead class="text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Coordinates</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Anomaly Score</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">FRP (MW)</th>
                  <th scope="col" class="py-2 text-right font-medium">Timestamp (UTC)</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="pt in topAnomalies"
                  :key="pt.id"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-mono font-medium text-ink-primary">
                    {{ pt.latitude.toFixed(4) }}, {{ pt.longitude.toFixed(4) }}
                  </th>
                  <td class="py-2 pr-4 text-right font-mono text-accent-bright">
                    {{ pt.score.toFixed(4) }}
                  </td>
                  <td class="py-2 pr-4 text-right">
                    {{ pt.frp !== null ? pt.frp.toFixed(1) : '—' }}
                  </td>
                  <td class="py-2 text-right font-mono text-ink-muted">
                    {{ pt.acq_datetime ?? '—' }}
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
