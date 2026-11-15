<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useApiFetch } from '@/api/useApiFetch'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import ConfidenceDbscanChart from '@/components/common/ConfidenceDbscanChart.vue'

const props = defineProps<{
  polygon?: GeoJSONPolygon | null
  metric?: 'raw' | 'harmonized'
}>()

const selectedYear = defineModel<number>('year', { default: 2025 })

const PointSchema = z.object({
  confidence: z.number().int(),
  count: z.number().int().nonnegative(),
  cluster: z.number().int(),
  is_anomaly: z.boolean(),
})

const ResponseSchema = z.object({
  summary: z.object({
    total_rows: z.number().int().nonnegative(),
    unique_values: z.number().int().nonnegative(),
    clusters_count: z.number().int().nonnegative(),
    anomaly_rows: z.number().int().nonnegative(),
    anomaly_pct: z.number(),
    eps: z.number(),
    min_samples: z.number().int(),
  }),
  points: z.array(PointSchema),
  anomalies: z.array(PointSchema).optional(),
})
type ConfidenceDbscanResponse = z.infer<typeof ResponseSchema>

const EPS_OPTIONS = [
  { value: '1', label: 'eps = 1' },
  { value: '2', label: 'eps = 2' },
  { value: '5', label: 'eps = 5' },
  { value: '10', label: 'eps = 10' },
] as const

const YEAR_OPTIONS = Array.from({ length: 26 }, (_, idx) => {
  const year = 2026 - idx
  return { value: year, label: String(year) }
})

const eps = shallowRef<'1' | '2' | '5' | '10'>('2')
const result = shallowRef<ConfidenceDbscanResponse | null>(null)
const isLoading = shallowRef(false)
const error = shallowRef<string | null>(null)
let latestRequest = 0

async function load() {
  const requestId = ++latestRequest
  isLoading.value = true
  error.value = null

  const params = new URLSearchParams({
    eps: eps.value,
    min_samples: '2',
    high_value: '90',
    metric: props.metric ?? 'raw',
    start_date: `${selectedYear.value}-01-01T00:00:00`,
    end_date: `${selectedYear.value}-12-31T23:59:59`,
  })
  if (props.polygon) {
    params.set('polygon', JSON.stringify(props.polygon))
  }

  const { data, error: fetchError } = await useApiFetch(
    `/dashboard/confidence-dbscan?${params.toString()}`,
  )
    .get()
    .json()

  if (requestId !== latestRequest) return
  try {
    if (fetchError.value || !data.value) {
      throw fetchError.value ?? new Error('The server returned no data.')
    }
    result.value = ResponseSchema.parse(data.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error.'
  } finally {
    isLoading.value = false
  }
}

watch([eps, selectedYear, () => props.polygon, () => props.metric], load, { immediate: true })

const points = computed(() => result.value?.points ?? [])
const isEmpty = computed(() => result.value !== null && points.value.length === 0)
const pctFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })

const summaryText = computed(() => {
  if (!result.value) return ''
  const s = result.value.summary
  return `In ${selectedYear.value}, grouped ${s.unique_values} unique confidence levels (${s.total_rows.toLocaleString()} rows) into ${s.clusters_count} DBSCAN ${s.clusters_count === 1 ? 'cluster' : 'clusters'} with ${s.anomaly_rows.toLocaleString()} isolated confidence rows (${pctFmt.format(s.anomaly_pct)}%).`
})

const chartDescription = computed(
  () => `DBSCAN confidence value distribution chart for ${selectedYear.value}. ${summaryText.value}`,
)
</script>

<template>
  <section aria-labelledby="confidence-dbscan-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="confidence-dbscan-title" class="text-base font-semibold text-ink-primary">
            Confidence value distribution &amp; DBSCAN clustering
          </h2>
          <span
            class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 text-[11px] text-ink-muted"
          >
            {{ polygon ? 'Drawn area (Polygon)' : 'All regions' }} ·
            {{ metric === 'harmonized' ? 'Harmonized' : 'Raw' }} · high_value=90
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Maps categorical VIIRS confidence (<code class="font-mono text-xs">l=15</code>,
          <code class="font-mono text-xs">n=50</code>, <code class="font-mono text-xs">h=90</code>)
          alongside numeric MODIS confidence (0–100) and clusters distinct values with 1D DBSCAN.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup v-model="eps" :options="EPS_OPTIONS" label="DBSCAN epsilon" />
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
        <span>Could not load confidence DBSCAN. {{ error }}</span>
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
        class="h-[20rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No confidence records found for {{ selectedYear }}.
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
          <ConfidenceDbscanChart :points="points" :description="chartDescription" />
        </div>

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          aria-label="Chart legend"
        >
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm bg-telemetry" />
            Dense confidence cluster
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm border border-accent-bright bg-accent-muted" />
            Isolated confidence value (DBSCAN -1)
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show confidence levels ({{ points.length }})</span>
            <span class="hidden group-open:inline">Hide confidence levels</span>
          </summary>
          <div class="max-h-72 overflow-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[28rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Confidence value counts and DBSCAN cluster assignment
              </caption>
              <thead class="sticky top-0 bg-surface-panel text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Confidence (%)</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Detections</th>
                  <th scope="col" class="py-2 font-medium">DBSCAN Assignment</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="pt in points"
                  :key="pt.confidence"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-mono font-medium text-ink-primary">
                    {{ pt.confidence }}%
                  </th>
                  <td class="py-2 pr-4 text-right">{{ pt.count.toLocaleString() }}</td>
                  <td
                    class="py-2"
                    :class="pt.is_anomaly ? 'text-accent-bright' : 'text-ink-secondary'"
                  >
                    {{ pt.is_anomaly ? 'Isolated anomaly (-1)' : `Cluster #${pt.cluster}` }}
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
