<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useTemporalChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useLocaleFormatters } from '@/i18n'
import { useChartFiltersStore } from '@/stores/chartFilters'
import AnnualActivityRenderer, {
  SERIES_COLORS,
  annualValue,
  completeYearMedian,
} from '@/components/common/AnnualActivityChart.vue'
import BaseChartLoading from '@/components/ui/BaseChartLoading.vue'
import AnnualActivityTable from '@/components/common/AnnualActivityTable.vue'

const { t } = useI18n()
const { locale, bcp47Locale } = useLocaleFormatters()
const filtersStore = useChartFiltersStore()
const { metric, activePolygon } = storeToRefs(filtersStore)
const { getAnnualStats } = useTemporalChartsApi()

const {
  data: result,
  isLoading,
  error,
  refresh,
} = useChartLifecycle({
  fetcher: () =>
    getAnnualStats({
      include_distributions: false,
      polygon: activePolygon.value,
    }),
  watchSources: [activePolygon],
})

const rows = computed(() => result.value?.rows ?? [])
const isEmpty = computed(
  () => result.value !== null && rows.value.every((row) => row.total_hotspots === 0),
)
const isHarmonized = computed(() => metric.value === 'harmonized')

const valueFormat = computed(
  () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: isHarmonized.value ? 1 : 0 }),
)
const pctFormat = computed(
  () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 0 }),
)

function describe(value: number) {
  return isHarmonized.value
    ? t('charts.annual.anIndexOf', { value: valueFormat.value.format(value) })
    : t('charts.annual.detectionsCount', { value: valueFormat.value.format(value) })
}

const summary = computed(() => {
  const complete = rows.value.filter((row) => row.complete)
  if (complete.length === 0) return t('charts.annual.noCompleteYear')
  const ranked = [...complete].sort(
    (a, b) => annualValue(b, metric.value) - annualValue(a, metric.value),
  )
  const busiest = ranked[0]!
  const quietest = ranked[ranked.length - 1]!
  const median = completeYearMedian(rows.value, metric.value)
  const busiestValue = annualValue(busiest, metric.value)
  const vsMedian =
    median !== null && median > 0
      ? t('charts.annual.vsMedianPct', {
          pct: pctFormat.value.format(((busiestValue - median) / median) * 100),
        })
      : ''
  return t('charts.annual.busiestSummary', {
    busiest: busiest.year,
    detail: describe(busiestValue),
    vsMedian,
    quietest: quietest.year,
  })
})

const provisionalNote = computed(() => {
  const years = rows.value.filter((row) => row.provisional_months > 0).map((row) => row.year)
  if (years.length === 0) return ''
  return t('charts.annual.provisionalNote', { years: years.join(', ') })
})

const hasProvisional = computed(() => rows.value.some((row) => row.provisional_months > 0))

const partialNote = computed(() => {
  const partial = rows.value.filter((row) => !row.complete && row.total_hotspots > 0)
  if (partial.length === 0) return ''
  const list = partial.map((row) =>
    t('charts.annual.monthsOf12', { year: row.year, months: row.months_in_archive }),
  )
  return t('charts.annual.partialNote', { list: list.join(', ') })
})

const rangeText = computed(() => {
  const range = result.value?.range
  return range ? t('charts.annual.rangeText', { start: range.start_year, end: range.end_year }) : ''
})

const harmonizedMissing = computed(
  () =>
    isHarmonized.value &&
    rows.value.some((row) => row.total_hotspots > 0) &&
    rows.value.every((row) => row.harmonized_index === 0),
)

const chartDescription = computed(() =>
  t('charts.annual.chartDesc', {
    what: isHarmonized.value ? t('charts.annual.whatHarmonized') : t('charts.annual.whatSensors'),
    range: rangeText.value,
    summary: summary.value,
  }),
)

const legend = computed(() =>
  isHarmonized.value
    ? [
        {
          key: 'harmonized',
          label: t('charts.annual.harmonizedIndex'),
          swatch: SERIES_COLORS.harmonized,
        },
      ]
    : [
        { key: 'modis', label: t('common.modis'), swatch: SERIES_COLORS.modis },
        { key: 'viirs', label: t('common.viirs'), swatch: SERIES_COLORS.viirs },
      ],
)
</script>

<template>
  <section aria-labelledby="annual-activity-title">
    <header class="border-b border-border-subtle p-5">
      <div class="max-w-[62ch]">
        <h2 id="annual-activity-title" class="text-base font-semibold text-ink-primary">
          {{ t('charts.annual.title') }}
        </h2>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          {{ t('charts.annual.subtitle') }}
        </p>
      </div>
    </header>

    <div class="space-y-4 p-5">
      <div
        v-if="error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-100"
      >
        <span>{{ t('charts.annual.errorLoad', { error }) }}</span>
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
        height-class="h-[20rem]"
        :label="t('charts.annual.loading')"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        {{ t('charts.annual.empty') }}
      </p>

      <template v-else-if="result !== null">
        <div class="space-y-1">
          <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoading">
            {{ summary }}
          </p>
          <p v-if="partialNote" class="text-xs text-ink-muted">{{ partialNote }}</p>
          <p v-if="provisionalNote" class="text-xs text-ink-muted">{{ provisionalNote }}</p>
        </div>

        <p
          v-if="harmonizedMissing"
          class="rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 text-[13px] text-accent-bright"
        >
          {{ t('charts.annual.harmonizedMissing') }}
        </p>

        <div
          :class="
            isLoading
              ? 'opacity-60 transition-opacity duration-200'
              : 'transition-opacity duration-200'
          "
        >
          <AnnualActivityRenderer
            :rows="rows"
            :metric="metric"
            :description="chartDescription"
            :lang="locale"
          />
        </div>

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          :aria-label="t('charts.annual.legendAria')"
        >
          <li v-for="item in legend" :key="item.key" class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm" :style="{ backgroundColor: item.swatch }" />
            {{ item.label }}
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm bg-slate-400/35" />
            {{ t('charts.annual.incompleteYear') }}
          </li>
          <li v-if="hasProvisional" class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm border border-dashed border-ink-primary" />
            {{ t('charts.annual.nearRealTime') }}
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-[1.5px] border-dashed border-ink-secondary" />
            {{ t('charts.annual.medianYear') }}
          </li>
          <li v-if="!isHarmonized" class="inline-flex items-center gap-2">
            <span class="h-3 border-l border-dotted border-accent" />
            {{ t('charts.annual.viirsStarts') }}
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">{{ t('charts.annual.showTable') }}</span>
            <span class="hidden group-open:inline">{{ t('charts.annual.hideTable') }}</span>
          </summary>
          <div class="border-t border-border-subtle px-4 pb-3">
            <AnnualActivityTable :rows="rows" :metric="metric" />
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
