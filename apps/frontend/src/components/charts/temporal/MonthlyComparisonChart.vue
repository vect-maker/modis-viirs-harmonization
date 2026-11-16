<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useTemporalChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useLocaleFormatters } from '@/i18n'
import { useChartFiltersStore } from '@/stores/chartFilters'
import BaseChartLoading from '@/components/ui/BaseChartLoading.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import MonthlyComparisonRenderer, {
  MIN_BASELINE_YEARS,
  STATUS_COLORS,
  monthStatus,
} from '@/components/common/MonthlyComparisonChart.vue'
import MonthlyComparisonTable from '@/components/common/MonthlyComparisonTable.vue'

const { t } = useI18n()
const { bcp47Locale } = useLocaleFormatters()
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
  metric.value === 'harmonized'
    ? t('charts.annual.harmonizedIndex').toLowerCase()
    : t('stats.detections').toLowerCase(),
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
  if (years.length === 0) return t('charts.monthly.baselineNone')
  const first = years[0]
  const last = years[years.length - 1]
  return t('charts.monthly.baseline', {
    count: years.length,
    unit: years.length === 1 ? t('charts.monthly.yearSingular') : t('charts.monthly.yearPlural'),
    first,
    last,
  })
})

const summary = computed(() => {
  const target = shownYear.value
  if (target === null) return ''
  const { above, below, comparable } = counts.value
  if (comparable === 0) {
    return (result.value?.baseline_years.length ?? 0) < MIN_BASELINE_YEARS
      ? t('charts.monthly.tooFewBaseline', { min: MIN_BASELINE_YEARS, year: target })
      : t('charts.monthly.noMonthData', { year: target })
  }
  const unit = comparable === 1 ? t('charts.monthly.monthSingular') : t('charts.monthly.monthPlural')
  return below > 0
    ? t('charts.monthly.summaryAboveAndBelow', { above, comparable, unit, year: target, below })
    : t('charts.monthly.summaryAbove', { above, comparable, unit, year: target })
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
    ? t('charts.monthly.chartDescEmpty')
    : t('charts.monthly.chartDesc', {
        label: valueLabel.value,
        year: shownYear.value,
        summary: summary.value,
      }),
)

const monthFormatter = computed(
  () => new Intl.DateTimeFormat(bcp47Locale.value, { month: 'short', timeZone: 'UTC' }),
)
const monthNames = (list: readonly { month: number }[]) =>
  list
    .map((m) => monthFormatter.value.format(new Date(Date.UTC(2024, m.month - 1, 1))))
    .join(', ')

const dataNotes = computed(() => {
  const target = shownYear.value
  const notes: string[] = []
  const missing = months.value.filter((m) => m.archive_state === 'missing')
  const lastWithData = Math.max(0, ...months.value.filter((m) => m.has_data).map((m) => m.month))
  const gaps = missing.filter((m) => m.month < lastWithData)
  if (gaps.length > 0) {
    notes.push(t('charts.monthly.gapNote', { months: monthNames(gaps), year: target }))
  }
  const partial = months.value.filter((m) => m.archive_state === 'partial')
  if (partial.length > 0) {
    notes.push(t('charts.monthly.partialNote', { months: monthNames(partial) }))
  }
  if (months.value.some((m) => m.provisional)) {
    notes.push(
      metric.value === 'harmonized'
        ? t('charts.monthly.nrtHarmonizedNote')
        : t('charts.monthly.nrtRawNote'),
    )
  }
  return notes
})

const legend = computed(() => {
  const items: { key: string; label: string; swatch: string; dashed?: boolean }[] = [
    { key: 'above', label: t('charts.monthly.aboveRange'), swatch: STATUS_COLORS.above },
    { key: 'typical', label: t('charts.monthly.typical'), swatch: STATUS_COLORS.typical },
    { key: 'below', label: t('charts.monthly.belowRange'), swatch: STATUS_COLORS.below },
  ]
  if (months.value.some((m) => m.archive_state === 'partial')) {
    items.push({ key: 'partial', label: t('charts.monthly.partialMonth'), swatch: STATUS_COLORS.partial })
  }
  if (months.value.some((m) => m.provisional)) {
    items.push({
      key: 'nrt',
      label: t('charts.monthly.nearRealTime'),
      swatch: 'transparent',
      dashed: true,
    })
  }
  return items
})
</script>

<template>
  <section aria-labelledby="monthly-comparison-title">
    <header class="flex flex-wrap items-start justify-between gap-4 border-b border-border-subtle p-5">
      <div class="max-w-[62ch]">
        <h2 id="monthly-comparison-title" class="text-base font-semibold text-ink-primary">
          {{ t('charts.monthly.title') }}
        </h2>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          {{ t('charts.monthly.subtitle') }}
        </p>
      </div>
      <div v-if="yearOptions.length > 0" class="flex items-center gap-2.5">
        <span id="monthly-year-label" class="text-xs font-medium text-ink-secondary">{{
          t('charts.monthly.year')
        }}</span>
        <BaseSelect
          v-model="selectedYear"
          :options="yearOptions"
          :label="t('charts.monthly.year')"
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
        <span>{{ t('charts.monthly.errorLoad', { error }) }}</span>
        <button
          type="button"
          class="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-red-300/40 px-3 text-xs font-medium hover:bg-red-400/10 focus-visible:outline-2 focus-visible:outline-focus"
          @click="refresh"
        >
          <RotateCw aria-hidden="true" class="h-3.5 w-3.5" />
          {{ t('common.retry') }}
        </button>
      </div>

      <BaseChartLoading
        v-if="result === null && isLoading"
        height-class="h-[21rem]"
        :label="t('charts.monthly.loading')"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        {{ t('charts.monthly.empty') }}
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
          {{ t('charts.monthly.harmonizedMissing') }}
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

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          :aria-label="t('charts.annual.legendAria')"
        >
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
            {{ t('charts.monthly.median') }}
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-5 rounded-sm bg-white/10" />
            {{ t('charts.monthly.typicalRange') }}
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">{{ t('charts.monthly.showTable') }}</span>
            <span class="hidden group-open:inline">{{ t('charts.monthly.hideTable') }}</span>
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
