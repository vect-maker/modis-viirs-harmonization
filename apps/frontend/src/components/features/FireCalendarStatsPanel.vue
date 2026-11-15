<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useApiFetch } from '@/api/useApiFetch'
import { ChartResponseSchema } from '@/api/modules/shared/schemas'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import FireCalendarStatsChart, {
  type FireCalendarIntervalItem,
} from '@/components/common/FireCalendarStatsChart.vue'

const props = defineProps<{
  polygon?: GeoJSONPolygon | null
  metric?: 'raw' | 'harmonized'
}>()

const selectedYear = defineModel<number>('year', { default: 2025 })

const { availableDates } = storeToRefs(useHotspotsStore())

const IntervalSchema = z.object({
  date: z.string(),
  has_data: z.boolean().optional(),
  archive_state: z.enum(['full', 'partial', 'missing']).optional(),
  hotspot_count: z.number().int().nonnegative(),
  fire_count: z.number().int().nonnegative(),
  new_fires: z.number().int().nonnegative(),
  active_fires: z.number().int().nonnegative(),
  frp_total: z.number(),
  frp_average: z.number(),
  max_frp: z.number(),
  daytime_hotspots: z.number().int().nonnegative(),
  nighttime_hotspots: z.number().int().nonnegative(),
  high_confidence_count: z.number().int().nonnegative(),
})

const ResponseSchema = z.object({
  period: z.object({
    year: z.number().int(),
    month: z.number().int().nullable(),
    start_date: z.string(),
    end_date: z.string(),
  }),
  aggregation: z.enum(['day', 'week', 'month']),
  total_hotspots: z.number().int().nonnegative(),
  total_fires: z.number().int().nonnegative(),
  new_fires: z.number().int().nonnegative(),
  active_fires: z.number().int().nonnegative(),
  frp_total: z.number(),
  frp_average: z.number(),
  max_frp: z.number(),
  daytime_hotspots: z.number().int().nonnegative(),
  nighttime_hotspots: z.number().int().nonnegative(),
  high_confidence_count: z.number().int().nonnegative(),
  intervals: z.array(IntervalSchema),
})
type FireCalendarResponse = z.infer<typeof ResponseSchema>

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

const result = shallowRef<FireCalendarResponse | null>(null)
const isLoading = shallowRef(false)
const error = shallowRef<string | null>(null)
let latestRequest = 0

async function load() {
  const requestId = ++latestRequest
  isLoading.value = true
  error.value = null

  const params = new URLSearchParams({
    year: String(selectedYear.value),
    aggregation: aggregation.value,
    metric: props.metric ?? 'raw',
  })
  if (instrument.value !== 'ALL') {
    params.set('instrument', instrument.value)
  }
  if (props.polygon) {
    params.set('polygon', JSON.stringify(props.polygon))
  }

  const { data, error: fetchError } = await useApiFetch(`/charts/temporal/fire-calendar?${params.toString()}`)
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

watch(
  [selectedYear, aggregation, instrument, () => props.polygon, () => props.metric],
  load,
  { immediate: true },
)

// Detectamos el hueco conocido de ene-mar 2026 y fechas posteriores al archivo para no graficarlos como 0 incendios.
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
            {{ polygon ? 'Drawn area (Polygon)' : 'All regions' }} ·
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
        No hotspot detections found for {{ selectedYear }} with the selected filters.
      </p>

      <template v-else-if="result !== null">
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
            <p class="text-[11px] text-ink-muted">Total Hotspots</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums text-accent-bright">
              {{ result.total_hotspots.toLocaleString() }}
            </p>
          </div>
          <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
            <p class="text-[11px] text-ink-muted">Day / Night Split</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums text-ink-primary">
              {{ dayPct }}% <span class="text-xs font-normal text-ink-muted">daytime</span>
            </p>
          </div>
          <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
            <p class="text-[11px] text-ink-muted">Average / Peak FRP</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums text-ink-primary">
              {{ frpFmt.format(result.frp_average) }}
              <span class="text-xs font-normal text-ink-muted">
                / {{ frpFmt.format(result.max_frp) }} MW
              </span>
            </p>
          </div>
          <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
            <p class="text-[11px] text-ink-muted">High Confidence</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums text-ink-primary">
              {{ result.high_confidence_count.toLocaleString() }}
            </p>
          </div>
        </div>

        <div class="space-y-1">
          <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoading">
            {{ summaryText }}
          </p>
          <p v-if="hasMissingGaps" class="text-xs text-ink-muted">
            Periods without archive coverage (such as Jan–Mar 2026) are masked as data gaps instead
            of zero fires, matching the Monthly Comparison chart.
          </p>
          <p v-if="result.total_fires === 0" class="text-xs text-ink-muted">
            Cluster-based fire counts (<code class="font-mono">total_fires</code>,
            <code class="font-mono">new_fires</code>, <code class="font-mono">active_fires</code>)
            read 0 because the persistent <code class="font-mono">fire_clusters</code> table is not
            populated; use the Movement &amp; ML tab for on-the-fly DBSCAN clustering.
          </p>
        </div>

        <div
          :class="
            isLoading
              ? 'opacity-60 transition-opacity duration-200'
              : 'transition-opacity duration-200'
          "
        >
          <FireCalendarStatsChart
            :intervals="intervals"
            :aggregation="aggregation"
            :description="chartDescription"
          />
        </div>

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          aria-label="Chart legend"
        >
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm bg-accent" />
            Daytime (D)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm bg-telemetry" />
            Nighttime (N)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-2 border-accent-bright" />
            Average FRP (MW)
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show interval values ({{ intervals.length }})</span>
            <span class="hidden group-open:inline">Hide interval values</span>
          </summary>
          <div class="max-h-80 overflow-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[38rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Fire calendar intervals for {{ selectedYear }}
              </caption>
              <thead class="sticky top-0 bg-surface-panel text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Period</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Hotspots</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Daytime</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Nighttime</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">High Conf.</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Avg FRP</th>
                  <th scope="col" class="py-2 text-right font-medium">Max FRP</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="item in intervals"
                  :key="item.date"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-medium text-ink-primary">
                    {{ item.date }}
                  </th>
                  <template v-if="item.missing">
                    <td colspan="6" class="py-2 text-right text-ink-muted">
                      No data in archive (gap)
                    </td>
                  </template>
                  <template v-else>
                    <td class="py-2 pr-4 text-right">{{ item.hotspot_count.toLocaleString() }}</td>
                    <td class="py-2 pr-4 text-right">
                      {{ item.daytime_hotspots.toLocaleString() }}
                    </td>
                    <td class="py-2 pr-4 text-right">
                      {{ item.nighttime_hotspots.toLocaleString() }}
                    </td>
                    <td class="py-2 pr-4 text-right">
                      {{ item.high_confidence_count.toLocaleString() }}
                    </td>
                    <td class="py-2 pr-4 text-right">{{ frpFmt.format(item.frp_average) }} MW</td>
                    <td class="py-2 text-right">{{ frpFmt.format(item.max_frp) }} MW</td>
                  </template>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
