<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { useTemporalChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useChartFiltersStore } from '@/stores/chartFilters'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import MonthlyComparisonRenderer, {
  MIN_BASELINE_YEARS,
  MONTH_LABELS,
  STATUS_COLORS,
  monthStatus,
} from '@/components/common/MonthlyComparisonChart.vue'
import MonthlyComparisonTable from '@/components/common/MonthlyComparisonTable.vue'

const filtersStore = useChartFiltersStore()
const { metric, activePolygon, selectedYear: storeYear } = storeToRefs(filtersStore)
const { getMonthlyComparison } = useTemporalChartsApi()

const requestedYear = shallowRef<number | null>(storeYear.value)

const {
  data: result,
  isLoading,
  error,
  refresh,
} = useChartLifecycle({
  fetcher: () =>
    getMonthlyComparison({
      metric: metric.value,
      year: requestedYear.value,
      polygon: activePolygon.value,
    }),
  watchSources: [metric, requestedYear, activePolygon],
})

const selectedYear = computed<number>({
  get: () => requestedYear.value ?? result.value?.year ?? 0,
  set: (value) => {
    requestedYear.value = value
    filtersStore.setSelectedYear(value)
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
    const status = monthStatus(month, metric.value)
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

const chartDescription = computed(() =>
  shownYear.value === null
    ? 'Monthly comparison chart'
    : `Bar chart of monthly ${valueLabel.value} in ${shownYear.value} against the median and typical range of other years. ${summary.value}`,
)

const monthNames = (list: readonly { month: number }[]) =>
  list.map((m) => MONTH_LABELS[m.month - 1]).join(', ')

const dataNotes = computed(() => {
  const target = shownYear.value
  const notes: string[] = []
  const missing = months.value.filter((m) => m.archive_state === 'missing')
  const lastWithData = Math.max(0, ...months.value.filter((m) => m.has_data).map((m) => m.month))
  const gaps = missing.filter((m) => m.month < lastWithData)
  if (gaps.length > 0) {
    notes.push(`The archive has no data for ${monthNames(gaps)} ${target}. Those months are gaps, not zero fires.`)
  }
  const partial = months.value.filter((m) => m.archive_state === 'partial')
  if (partial.length > 0) {
    notes.push(`${monthNames(partial)} only cover part of the month, so they are faded and not compared.`)
  }
  if (months.value.some((m) => m.provisional)) {
    notes.push(
      metric.value === 'harmonized'
        ? 'Months with a dashed outline come from the near-real-time feed, which is not harmonized yet, so they are not compared on this scale.'
        : 'Months with a dashed outline come from the near-real-time feed: not harmonized yet and with one more VIIRS satellite than the archive, so they read higher than earlier years.',
    )
  }
  return notes
})

const legend = computed(() => {
  const items: { key: string; label: string; swatch: string; dashed?: boolean }[] = [
    { key: 'above', label: 'Above range', swatch: STATUS_COLORS.above },
    { key: 'typical', label: 'Typical', swatch: STATUS_COLORS.typical },
    { key: 'below', label: 'Below range', swatch: STATUS_COLORS.below },
  ]
  if (months.value.some((m) => m.archive_state === 'partial')) {
    items.push({ key: 'partial', label: 'Partial month', swatch: STATUS_COLORS.partial })
  }
  if (months.value.some((m) => m.provisional)) {
    items.push({ key: 'nrt', label: 'Near real time', swatch: 'transparent', dashed: true })
  }
  return items
})
</script>

<template>
  <section aria-labelledby="monthly-comparison-title">
    <header class="flex flex-wrap items-start justify-between gap-4 border-b border-border-subtle p-5">
      <div class="max-w-[62ch]">
        <h2 id="monthly-comparison-title" class="text-base font-semibold text-ink-primary">
          This year against the typical range
        </h2>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Each month compared against the median of the other years in the archive. The shaded band
          shows the middle 50% of years (25th to 75th percentile); bars above it mark an unusually
          active month.
        </p>
      </div>
      <div v-if="yearOptions.length > 0" class="flex items-center gap-2.5">
        <span id="monthly-year-label" class="text-xs font-medium text-ink-secondary">Year</span>
        <BaseSelect
          v-model="selectedYear"
          :options="yearOptions"
          label="Year"
          aria-labelledby="monthly-year-label"
          :disabled="isLoading"
        />
      </div>
    </header>

    <div class="space-y-4 p-5">
      <div
        v-if="error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-100"
      >
        <span>Could not load the monthly comparison. {{ error }}</span>
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
        class="h-[21rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No hotspot records are loaded yet.
      </p>

      <template v-else-if="result !== null">
        <div class="space-y-1">
          <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoading">
            {{ summary }}
          </p>
          <p class="text-xs text-ink-muted">{{ baselineText }}</p>
          <p v-for="(note, index) in dataNotes" :key="index" class="text-xs text-ink-muted">
            {{ note }}
          </p>
        </div>

        <p
          v-if="harmonizedMissing"
          class="rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 text-[13px] text-accent-bright"
        >
          The database has detections for this area, but no harmonized weights yet. Load the output
          of the harmonization step, or switch to Detections.
        </p>

        <div
          :class="
            isLoading
              ? 'opacity-60 transition-opacity duration-200'
              : 'transition-opacity duration-200'
          "
        >
          <MonthlyComparisonRenderer
            :months="months"
            :year="shownYear ?? selectedYear"
            :value-label="valueLabel"
            :fraction-digits="fractionDigits"
            :metric="metric"
            :description="chartDescription"
          />
        </div>

        <ul class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary" aria-label="Chart legend">
          <li v-for="item in legend" :key="item.key" class="inline-flex items-center gap-2">
            <span
              class="h-3 w-3 rounded-sm"
              :class="item.dashed ? 'border border-dashed border-ink-primary' : ''"
              :style="{ backgroundColor: item.swatch }"
            />
            {{ item.label }}
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-2 border-dashed border-ink-secondary" />
            Median
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-5 rounded-sm bg-white/10" />
            Typical range (25th to 75th pct)
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show monthly table</span>
            <span class="hidden group-open:inline">Hide monthly table</span>
          </summary>
          <div class="border-t border-border-subtle px-4 pb-3">
            <MonthlyComparisonTable
              :months="months"
              :year="shownYear ?? selectedYear"
              :fraction-digits="fractionDigits"
              :metric="metric"
              :value-label="valueLabel"
            />
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
