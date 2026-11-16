<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useTemporalChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useLocaleFormatters } from '@/i18n'
import { useChartFiltersStore } from '@/stores/chartFilters'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseChartLoading from '@/components/ui/BaseChartLoading.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import FireCalendarStatsRenderer, {
  type FireCalendarIntervalItem,
} from '@/components/common/FireCalendarStatsChart.vue'

const { t } = useI18n()
const { bcp47Locale, formatInt } = useLocaleFormatters()
const filtersStore = useChartFiltersStore()
const { metric, activePolygon, selectedYear: storeYear } = storeToRefs(filtersStore)
const { availableDates } = storeToRefs(useHotspotsStore())
const { getFireCalendar } = useTemporalChartsApi()

const selectedYear = computed<number>({
  get: () => storeYear.value,
  set: (value) => filtersStore.setSelectedYear(value),
})

type Aggregation = 'month' | 'week' | 'day'
type SensorOption = 'ALL' | 'MODIS' | 'VIIRS'

const AGGREGATION_OPTIONS = computed(
  () =>
    [
      { value: 'month', label: t('charts.fireCalendar.monthly') },
      { value: 'week', label: t('charts.fireCalendar.weekly') },
      { value: 'day', label: t('charts.fireCalendar.daily') },
    ] as const satisfies readonly { value: Aggregation; label: string }[],
)

const SENSOR_OPTIONS = computed(
  () =>
    [
      { value: 'ALL', label: t('charts.fireCalendar.allSensors') },
      { value: 'MODIS', label: t('common.modis') },
      { value: 'VIIRS', label: t('common.viirs') },
    ] as const satisfies readonly { value: SensorOption; label: string }[],
)

const YEAR_OPTIONS = Array.from({ length: 26 }, (_, idx) => {
  const year = 2026 - idx
  return { value: year, label: String(year) }
})

const aggregation = shallowRef<Aggregation>('month')
const instrument = shallowRef<SensorOption>('ALL')

const {
  data: result,
  isLoading,
  error,
  refresh,
} = useChartLifecycle({
  fetcher: () =>
    getFireCalendar({
      year: selectedYear.value,
      aggregation: aggregation.value,
      metric: metric.value,
      instrument: instrument.value !== 'ALL' ? instrument.value : undefined,
      polygon: activePolygon.value,
    }),
  watchSources: [selectedYear, aggregation, instrument, activePolygon, metric],
})

function isMissingBucket(dateStr: string): boolean {
  const maxDate = availableDates.value?.end
  if (maxDate && dateStr > maxDate) return true
  if (dateStr.startsWith('2026-01') || dateStr.startsWith('2026-02') || dateStr.startsWith('2026-03')) {
    return true
  }
  if (aggregation.value !== 'month' && dateStr >= '2026-04-01' && dateStr <= '2026-04-29') {
    return true
  }
  return false
}

const intervals = computed<readonly FireCalendarIntervalItem[]>(() =>
  (result.value?.intervals ?? []).map((item) => ({
    ...item,
    missing:
      item.has_data === false ||
      item.archive_state === 'missing' ||
      (item.hotspot_count === 0 && isMissingBucket(item.date)),
  })),
)

const hasMissingGaps = computed(() => intervals.value.some((i) => i.missing))
const isEmpty = computed(() => result.value !== null && result.value.total_hotspots === 0)
const frpFmt = computed(() => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 1 }))
const pctFmt = computed(() => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 1 }))

const dayPct = computed(() => {
  const tot = result.value?.total_hotspots ?? 0
  if (tot === 0) return '0'
  return pctFmt.value.format(((result.value?.daytime_hotspots ?? 0) / tot) * 100)
})

const summaryText = computed(() => {
  if (!result.value) return ''
  const r = result.value
  const scope = activePolygon.value
    ? t('charts.fireCalendar.inSelectedArea')
    : t('charts.fireCalendar.acrossRegionalArchive')
  return t('charts.fireCalendar.summary', {
    year: r.period.year,
    total: formatInt(r.total_hotspots),
    scope,
    dayPct: dayPct.value,
    highConf: formatInt(r.high_confidence_count),
    avgFrp: frpFmt.value.format(r.frp_average),
    maxFrp: frpFmt.value.format(r.max_frp),
  })
})

const chartDescription = computed(() =>
  t('charts.fireCalendar.chartDesc', {
    agg: aggregation.value,
    year: selectedYear.value,
    summary: summaryText.value,
  }),
)
</script>

<template>
  <section aria-labelledby="fire-calendar-stats-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="fire-calendar-stats-title" class="text-base font-semibold text-ink-primary">
            {{ t('charts.fireCalendar.title') }}
          </h2>
          <span
            class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 text-[11px] text-ink-muted"
          >
            {{ activePolygon ? t('stats.drawnArea') : t('stats.allRegions') }} ·
            {{ metric === 'harmonized' ? t('stats.harmonizedIndex') : t('stats.detections') }}
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          {{ t('charts.fireCalendar.subtitle') }}
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup
          v-model="aggregation"
          :options="AGGREGATION_OPTIONS"
          :label="t('charts.fireCalendar.aggregation')"
        />
        <BaseToggleGroup
          v-model="instrument"
          :options="SENSOR_OPTIONS"
          :label="t('charts.fireCalendar.sensor')"
        />
        <BaseSelect
          v-model="selectedYear"
          :options="YEAR_OPTIONS"
          :label="t('charts.fireCalendar.year')"
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
        <span>{{ t('charts.fireCalendar.errorLoad', { error }) }}</span>
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
        :label="t('charts.fireCalendar.loading')"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        {{ t('charts.fireCalendar.empty') }}
      </p>

      <template v-else-if="result !== null">
        <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoading">
          {{ summaryText }}
        </p>

        <p
          v-if="hasMissingGaps"
          class="rounded-lg border border-border-subtle bg-white/[0.03] px-3.5 py-2.5 text-xs text-ink-muted"
        >
          {{ t('charts.fireCalendar.missingNote') }}
        </p>

        <div
          :class="
            isLoading
              ? 'opacity-60 transition-opacity duration-200'
              : 'transition-opacity duration-200'
          "
        >
          <FireCalendarStatsRenderer
            :intervals="intervals"
            :aggregation="aggregation"
            :description="chartDescription"
          />
        </div>
      </template>
    </div>
  </section>
</template>
