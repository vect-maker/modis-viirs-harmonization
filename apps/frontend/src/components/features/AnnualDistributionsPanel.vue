<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useApiFetch } from '@/api/useApiFetch'
import { ChartResponseSchema } from '@/api/modules/shared/schemas'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import AnnualDistributionsChart, {
  VARIABLE_META,
  type DistributionVariable,
} from '@/components/common/AnnualDistributionsChart.vue'

const props = defineProps<{
  polygon: GeoJSONPolygon | null
  year?: number
  metric?: 'raw' | 'harmonized'
}>()

const StatsSchema = z
  .object({
    count: z.number().int().nonnegative(),
    sum: z.number().nullable(),
    mean: z.number().nullable(),
    std: z.number().nullable(),
    min: z.number().nullable(),
    p25: z.number().nullable(),
    median: z.number().nullable(),
    p75: z.number().nullable(),
    p90: z.number().nullable(),
    iqr: z.number().nullable(),
    max: z.number().nullable(),
  })
  .nullable()

const ResponseSchema = z.object({
  range: z.object({ start_year: z.number().int(), end_year: z.number().int() }).nullable(),
  coverage: z.object({ first_detection: z.string(), last_detection: z.string() }).nullable(),
  rows: z.array(
    z.object({
      year: z.number().int(),
      months_in_archive: z.number().int().min(0).max(12),
      complete: z.boolean(),
      provisional_months: z.number().int().min(0).max(12).default(0),
      total_hotspots: z.number().int().nonnegative(),
      frp: StatsSchema,
      confidence: StatsSchema,
      bright_tir: StatsSchema,
      bright_mir: StatsSchema,
    }),
  ),
})
type DistributionsResponse = z.infer<typeof ResponseSchema>

const VARIABLE_OPTIONS = [
  { value: 'frp', label: 'FRP (MW)' },
  { value: 'confidence', label: 'Confidence (%)' },
  { value: 'bright_tir', label: 'TIR (K)' },
  { value: 'bright_mir', label: 'MIR (K)' },
] as const satisfies readonly { value: DistributionVariable; label: string }[]

const WINDOW_OPTIONS = [
  { value: '2021-2025', label: '2021 – 2025 (Complete archive)' },
  { value: '2022-2026', label: '2022 – 2026 (Includes NRT)' },
  { value: '2018-2025', label: '2018 – 2025 (8 years)' },
  { value: '2012-2025', label: '2012 – 2025 (VIIRS era)' },
  { value: '2001-2011', label: '2001 – 2011 (MODIS only)' },
] as const

const selectedVariable = shallowRef<DistributionVariable>('frp')
const selectedWindow = shallowRef<string>('2021-2025')
const result = shallowRef<DistributionsResponse | null>(null)
const isLoading = shallowRef(false)
const error = shallowRef<string | null>(null)
let latestRequest = 0

watch(
  () => props.year,
  (yr) => {
    if (!yr) return
    if (yr === 2026) {
      selectedWindow.value = '2022-2026'
    } else if (yr >= 2021 && yr <= 2025) {
      selectedWindow.value = '2021-2025'
    } else if (yr >= 2018 && yr <= 2025) {
      selectedWindow.value = '2018-2025'
    } else if (yr >= 2012 && yr <= 2025) {
      selectedWindow.value = '2012-2025'
    } else if (yr < 2012) {
      selectedWindow.value = '2001-2011'
    }
  },
  { immediate: true },
)

async function load() {
  const requestId = ++latestRequest
  isLoading.value = true
  error.value = null

  const [startStr, endStr] = selectedWindow.value.split('-')
  // Unificamos high_value=90 para que la media/mediana de confidence coincida con Correlations y DBSCAN.
  const params = new URLSearchParams({
    include_distributions: 'true',
    high_value: '90',
    metric: props.metric ?? 'raw',
    start_year: startStr ?? '2021',
    end_year: endStr ?? '2025',
  })
  if (props.polygon) params.set('polygon', JSON.stringify(props.polygon))

  const { data, error: fetchError } = await useApiFetch(
    `/charts/temporal/annual-stats?${params.toString()}`,
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

watch([selectedWindow, () => props.polygon, () => props.metric], load, { immediate: true })

const rows = computed(() => result.value?.rows ?? [])
const isEmpty = computed(
  () => result.value !== null && rows.value.every((r) => r.total_hotspots === 0),
)
const meta = computed(() => VARIABLE_META[selectedVariable.value])
const numFmt = computed(
  () => new Intl.NumberFormat('en-US', { maximumFractionDigits: meta.value.digits }),
)

function fmt(val: number | null | undefined): string {
  return val === null || val === undefined ? '—' : numFmt.value.format(val)
}

const summaryText = computed(() => {
  const valid = rows.value.filter((r) => (r[selectedVariable.value]?.count ?? 0) > 0)
  if (valid.length === 0) return 'No observations available for this variable and period.'
  const peak = [...valid].sort(
    (a, b) => (b[selectedVariable.value]?.median ?? 0) - (a[selectedVariable.value]?.median ?? 0),
  )[0]!
  const stat = peak[selectedVariable.value]!
  return `Highest median ${meta.value.label} in this window occurred in ${peak.year} at ${fmt(stat.median)} ${meta.value.unit} (IQR ${fmt(stat.p25)}–${fmt(stat.p75)} ${meta.value.unit}, P90 ${fmt(stat.p90)} ${meta.value.unit}).`
})

const chartDescription = computed(
  () => `Yearly distribution chart for ${meta.value.label}. ${summaryText.value}`,
)
</script>

<template>
  <section aria-labelledby="annual-distributions-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="annual-distributions-title" class="text-base font-semibold text-ink-primary">
            Annual thermal &amp; confidence distributions
          </h2>
          <span
            class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 text-[11px] text-ink-muted"
          >
            Physical sensor values · high_value=90
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Exact SQL percentiles (<code class="font-mono text-xs text-ink-secondary">PERCENTILE_CONT</code>)
          for Fire Radiative Power, confidence, and brightness temperatures (TIR/MIR). Respects the
          exact drawn polygon in PostGIS.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup
          v-model="selectedVariable"
          :options="VARIABLE_OPTIONS"
          label="Distribution variable"
        />
        <BaseSelect
          v-model="selectedWindow"
          :options="WINDOW_OPTIONS"
          label="Year window"
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
        <span>Could not load annual distributions. {{ error }}</span>
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
        class="h-[21rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No hotspot records are loaded for this selection yet.
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
          <AnnualDistributionsChart
            :rows="rows"
            :variable="selectedVariable"
            :description="chartDescription"
          />
        </div>

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          aria-label="Chart legend"
        >
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm bg-accent" />
            Median (P50)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-2 border-dashed border-telemetry" />
            Mean
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-2 border-dotted border-accent-bright" />
            90th percentile (P90)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-5 rounded-sm bg-accent/20 ring-1 ring-accent/40" />
            Interquartile range (P25–P75)
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show percentile table</span>
            <span class="hidden group-open:inline">Hide percentile table</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[38rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Annual percentiles for {{ meta.label }}
              </caption>
              <thead class="text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Year</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Count</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">P25</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Median</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Mean</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">P75</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">P90</th>
                  <th scope="col" class="py-2 text-right font-medium">Max</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="row in rows"
                  :key="row.year"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-medium text-ink-primary">{{ row.year }}</th>
                  <td class="py-2 pr-4 text-right">
                    {{ (row[selectedVariable]?.count ?? 0).toLocaleString() }}
                  </td>
                  <td class="py-2 pr-4 text-right">{{ fmt(row[selectedVariable]?.p25) }}</td>
                  <td class="py-2 pr-4 text-right text-accent-bright">
                    {{ fmt(row[selectedVariable]?.median) }}
                  </td>
                  <td class="py-2 pr-4 text-right">{{ fmt(row[selectedVariable]?.mean) }}</td>
                  <td class="py-2 pr-4 text-right">{{ fmt(row[selectedVariable]?.p75) }}</td>
                  <td class="py-2 pr-4 text-right">{{ fmt(row[selectedVariable]?.p90) }}</td>
                  <td class="py-2 text-right">{{ fmt(row[selectedVariable]?.max) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
