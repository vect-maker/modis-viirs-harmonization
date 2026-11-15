<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { useTemporalChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useChartFiltersStore } from '@/stores/chartFilters'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import FireCalendarStatsRenderer, {
  type FireCalendarIntervalItem,
} from '@/components/common/FireCalendarStatsChart.vue'

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

const AGGREGATION_OPTIONS = [
  { value: 'month', label: 'Monthly' },
  { value: 'week', label: 'Weekly' },
  { value: 'day', label: 'Daily' },
] as const satisfies readonly { value: Aggregation; label: string }[]

const SENSOR_OPTIONS = [
  { value: 'ALL', label: 'All sensors' },
  { value: 'MODIS', label: 'MODIS' },
  { value: 'VIIRS', label: 'VIIRS' },
] as const satisfies readonly { value: SensorOption; label: string }[]

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
const frpFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })
const pctFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

const dayPct = computed(() => {
  const tot = result.value?.total_hotspots ?? 0
  if (tot === 0) return '0'
  return pctFmt.format(((result.value?.daytime_hotspots ?? 0) / tot) * 100)
})

const summaryText = computed(() => {
  if (!result.value) return ''
  const r = result.value
  return `In ${r.period.year}, ${r.total_hotspots.toLocaleString()} detections were recorded across the global archive (${dayPct.value}% daytime, ${r.high_confidence_count.toLocaleString()} high confidence) with an average radiative power of ${frpFmt.format(r.frp_average)} MW and peak of ${frpFmt.format(r.max_frp)} MW.`
})

const chartDescription = computed(
  () =>
    `Stacked bar and line chart of ${aggregation.value} daytime and nighttime hotspots and average FRP in ${selectedYear.value}. ${summaryText.value}`,
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
            Fire calendar: diurnal cycle &amp; radiative power
          </h2>
          <span
            class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 text-[11px] text-ink-muted"
          >
            {{ activePolygon ? 'Drawn area (Polygon)' : 'All regions' }} ·
            {{ metric === 'harmonized' ? 'Harmonized index' : 'Raw detections' }}
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Aggregates detections by day, week, or month, splitting daytime (D) and nighttime (N)
          overpasses alongside mean and peak Fire Radiative Power (FRP).
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup
          v-model="aggregation"
          :options="AGGREGATION_OPTIONS"
          label="Time aggregation"
        />
        <BaseToggleGroup v-model="instrument" :options="SENSOR_OPTIONS" label="Sensor filter" />
        <BaseSelect
          v-model="selectedYear"
          :options="YEAR_OPTIONS"
          label="Calendar year"
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
        <span>Could not load fire calendar statistics. {{ error }}</span>
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
        No detections found for {{ selectedYear }} with the current sensor filter.
      </p>

      <template v-else-if="result !== null">
        <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoading">
          {{ summaryText }}
        </p>

        <p
          v-if="hasMissingGaps"
          class="rounded-lg border border-border-subtle bg-white/[0.03] px-3.5 py-2.5 text-xs text-ink-muted"
        >
          Unrecorded dates (such as the Jan–Mar 2026 archive gap or future months) are shown as
          gaps rather than zero fires.
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
