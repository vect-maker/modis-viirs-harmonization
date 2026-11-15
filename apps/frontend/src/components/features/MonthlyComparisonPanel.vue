<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import { useApiFetch } from '@/api/useApiFetch'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import MonthlyComparisonChart, {
  MIN_BASELINE_YEARS,
  STATUS_COLORS,
  monthStatus,
} from '@/components/common/MonthlyComparisonChart.vue'
import MonthlyComparisonTable from '@/components/common/MonthlyComparisonTable.vue'

type Metric = 'raw' | 'harmonized'
type AreaScope = 'area' | 'all'

const nullableNumber = z.number().nullable()
const ResponseSchema = z.object({
  year: z.number().int().nullable(),
  metric: z.enum(['raw', 'harmonized']),
  available_years: z.array(z.number().int()),
  baseline_years: z.array(z.number().int()),
  coverage: z
    .object({ first_detection: z.iso.date(), last_detection: z.iso.date() })
    .nullable(),
  months: z.array(
    z.object({
      month: z.number().int().min(1).max(12),
      has_data: z.boolean(),
      year_count: nullableNumber,
      year_raw_count: z.number().int().nullable(),
      anomaly_pct_median: nullableNumber,
      historic: z.object({
        count: z.number().int().nonnegative(),
        p25: nullableNumber,
        median: nullableNumber,
        p75: nullableNumber,
        max: nullableNumber,
      }),
    }),
  ),
})
type ComparisonResponse = z.infer<typeof ResponseSchema>

const METRIC_OPTIONS = [
  { value: 'raw', label: 'Detections' },
  { value: 'harmonized', label: 'Harmonized index' },
] as const satisfies readonly { value: Metric; label: string }[]

const AREA_OPTIONS = [
  { value: 'area', label: 'Drawn area' },
  { value: 'all', label: 'All regions' },
] as const satisfies readonly { value: AreaScope; label: string }[]

const { selectedPolygon } = storeToRefs(useHotspotsStore())

const metric = shallowRef<Metric>('raw')
const areaScope = shallowRef<AreaScope>(selectedPolygon.value ? 'area' : 'all')
/** null = el año más reciente con datos (lo resuelve el backend). */
const requestedYear = shallowRef<number | null>(null)

const result = shallowRef<ComparisonResponse | null>(null)
const isLoading = shallowRef(false)
const error = shallowRef<string | null>(null)
let latestRequest = 0

const activePolygon = computed(() =>
  areaScope.value === 'area' ? selectedPolygon.value : null,
)

async function load() {
  const requestId = ++latestRequest
  isLoading.value = true
  error.value = null

  const params = new URLSearchParams({ metric: metric.value })
  if (requestedYear.value !== null) params.set('year', String(requestedYear.value))
  if (activePolygon.value) params.set('polygon', JSON.stringify(activePolygon.value))

  const { data, error: fetchError } = await useApiFetch(
    `/dashboard/monthly-comparison?${params.toString()}`,
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

watch([metric, requestedYear, activePolygon], load, { immediate: true })
watch(selectedPolygon, (polygon) => {
  if (!polygon) areaScope.value = 'all'
})

const selectedYear = computed<number>({
  get: () => requestedYear.value ?? result.value?.year ?? 0,
  set: (value) => {
    requestedYear.value = value
  },
})

const yearOptions = computed(() =>
  [...(result.value?.available_years ?? [])]
    .reverse()
    .map((value) => ({ value, label: String(value) })),
)

const fractionDigits = computed(() => (metric.value === 'harmonized' ? 1 : 0))
const valueLabel = computed(() =>
  metric.value === 'harmonized' ? 'harmonized index' : 'detections',
)

const months = computed(() => result.value?.months ?? [])
const shownYear = computed(() => result.value?.year ?? null)

const counts = computed(() => {
  const tally = { above: 0, below: 0, comparable: 0 }
  for (const month of months.value) {
    const status = monthStatus(month)
    if (status === 'above') tally.above += 1
    if (status === 'below') tally.below += 1
    if (status === 'above' || status === 'below' || status === 'typical') tally.comparable += 1
  }
  return tally
})

const baselineText = computed(() => {
  const years = result.value?.baseline_years ?? []
  if (years.length === 0) return 'No other years in the archive to compare against.'
  const first = years[0]
  const last = years[years.length - 1]
  return `Baseline: ${years.length} other ${years.length === 1 ? 'year' : 'years'} from ${first} to ${last}.`
})

const summary = computed(() => {
  const target = shownYear.value
  if (target === null) return ''
  const { above, below, comparable } = counts.value
  if (comparable === 0) {
    return (result.value?.baseline_years.length ?? 0) < MIN_BASELINE_YEARS
      ? `There are fewer than ${MIN_BASELINE_YEARS} other years in the archive, so ${target} has no typical range to compare against.`
      : `No month of ${target} has data to compare yet.`
  }
  const aboveText = `${above} of ${comparable} ${comparable === 1 ? 'month' : 'months'} in ${target} ran above the typical range`
  return below > 0 ? `${aboveText} and ${below} ran below it.` : `${aboveText}.`
})

const isEmpty = computed(() => result.value !== null && result.value.coverage === null)
const harmonizedMissing = computed(
  () =>
    metric.value === 'harmonized' &&
    months.value.length > 0 &&
    months.value.every((m) => (m.year_count ?? 0) === 0 && (m.historic.max ?? 0) === 0) &&
    months.value.some((m) => (m.year_raw_count ?? 0) > 0),
)

const metricHelp = computed(() =>
  metric.value === 'harmonized'
    ? 'Weights MODIS detections so years before and after the 2012 VIIRS launch can be compared on one scale. Experimental index, not a fire count.'
    : 'Raw MODIS and VIIRS detections. VIIRS adds many small fires from 2012 on, so earlier years read low on this scale.',
)

const chartDescription = computed(() =>
  shownYear.value === null
    ? 'Monthly comparison chart'
    : `Bar chart of monthly ${valueLabel.value} in ${shownYear.value} against the median and typical range of other years. ${summary.value}`,
)

const legend = computed(() => [
  { key: 'above', label: 'Above range', swatch: STATUS_COLORS.above },
  { key: 'typical', label: 'Typical', swatch: STATUS_COLORS.typical },
  { key: 'below', label: 'Below range', swatch: STATUS_COLORS.below },
])
</script>

<template>
  <section aria-labelledby="monthly-comparison-title">
    <header class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between">
      <div class="max-w-[62ch]">
        <h2 id="monthly-comparison-title" class="text-base font-semibold text-ink-primary">
          Monthly activity against the historical baseline
        </h2>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Each bar is one month of the selected year. The shaded band is the typical range of the
          other years in the archive (25th to 75th percentile) and the dashed line is their median.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <BaseSelect
          v-if="yearOptions.length > 0"
          v-model="selectedYear"
          :options="yearOptions"
          label="Year to compare"
          :disabled="isLoading && result === null"
        />
        <BaseToggleGroup v-model="metric" :options="METRIC_OPTIONS" label="Metric" />
        <BaseToggleGroup
          v-if="selectedPolygon"
          v-model="areaScope"
          :options="AREA_OPTIONS"
          label="Area"
        />
      </div>
    </header>

    <div class="space-y-4 p-5">
      <p class="text-xs leading-relaxed text-ink-muted">
        {{ metricHelp }}
        <template v-if="!selectedPolygon">
          Showing all regions. To compare a specific place, collapse this panel and draw an area
          on the map.
        </template>
      </p>

      <div
        v-if="error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-100"
      >
        <span>Could not load the comparison. {{ error }}</span>
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
        class="h-[22rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No hotspot records are loaded for this selection yet.
      </p>

      <template v-else-if="result !== null && shownYear !== null">
        <div class="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoading">
            {{ summary }}
          </p>
          <p class="text-xs text-ink-muted">{{ baselineText }}</p>
        </div>

        <p
          v-if="harmonizedMissing"
          class="rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 text-[13px] text-accent-bright"
        >
          The database has detections but no harmonized weights yet. Load the output of the
          harmonization step, or switch to Detections.
        </p>

        <div :class="isLoading ? 'opacity-60 transition-opacity duration-200' : 'transition-opacity duration-200'">
          <MonthlyComparisonChart
            :months="months"
            :year="shownYear"
            :value-label="valueLabel"
            :fraction-digits="fractionDigits"
            :description="chartDescription"
          />
        </div>

        <ul class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary" aria-label="Chart legend">
          <li v-for="item in legend" :key="item.key" class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm" :style="{ backgroundColor: item.swatch }" />
            {{ item.label }}
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-5 rounded-sm bg-slate-300/[0.11] ring-1 ring-slate-300/20" />
            Typical range
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-[1.5px] border-dashed border-ink-secondary" />
            Median
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show monthly values</span>
            <span class="hidden group-open:inline">Hide monthly values</span>
          </summary>
          <div class="border-t border-border-subtle px-4 pb-3">
            <MonthlyComparisonTable
              :months="months"
              :year="shownYear"
              :value-label="valueLabel"
              :fraction-digits="fractionDigits"
            />
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
