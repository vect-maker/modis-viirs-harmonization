<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useApiFetch } from '@/api/useApiFetch'
import { ChartResponseSchema } from '@/api/modules/shared/schemas'
import AnnualActivityChart, {
  SERIES_COLORS,
  annualValue,
  completeYearMedian,
} from '@/components/common/AnnualActivityChart.vue'
import AnnualActivityTable from '@/components/common/AnnualActivityTable.vue'

const props = defineProps<{
  metric: 'raw' | 'harmonized'
  /** Polígono dibujado en el mapa, o null para todas las regiones. */
  polygon: GeoJSONPolygon | null
}>()

const ResponseSchema = z.object({
  range: z.object({ start_year: z.number().int(), end_year: z.number().int() }).nullable(),
  coverage: z
    .object({ first_detection: z.iso.date(), last_detection: z.iso.date() })
    .nullable(),
  rows: z.array(
    z.object({
      year: z.number().int(),
      months_in_archive: z.number().int().min(0).max(12),
      complete: z.boolean(),
      provisional_months: z.number().int().min(0).max(12).default(0),
      total_hotspots: z.number().int().nonnegative(),
      modis_count: z.number().int().nonnegative(),
      viirs_count: z.number().int().nonnegative(),
      harmonized_index: z.number(),
    }),
  ),
})
const EnvelopeSchema = ChartResponseSchema(ResponseSchema)
type AnnualResponse = z.infer<typeof ResponseSchema>

const result = shallowRef<AnnualResponse | null>(null)
const isLoading = shallowRef(false)
const error = shallowRef<string | null>(null)
let latestRequest = 0

// La métrica solo cambia cómo se dibuja; el área sí requiere pedir los datos de nuevo.
async function load() {
  const requestId = ++latestRequest
  isLoading.value = true
  error.value = null

  const params = new URLSearchParams({ include_distributions: 'false' })
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
    result.value = EnvelopeSchema.parse(data.value).data
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error.'
  } finally {
    isLoading.value = false
  }
}

watch(() => props.polygon, load, { immediate: true })

const rows = computed(() => result.value?.rows ?? [])
const isEmpty = computed(
  () => result.value !== null && rows.value.every((row) => row.total_hotspots === 0),
)
const isHarmonized = computed(() => props.metric === 'harmonized')

const valueFormat = computed(
  () => new Intl.NumberFormat('en-US', { maximumFractionDigits: isHarmonized.value ? 1 : 0 }),
)
const pctFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

function describe(value: number) {
  return isHarmonized.value
    ? `an index of ${valueFormat.value.format(value)}`
    : `${valueFormat.value.format(value)} detections`
}

const summary = computed(() => {
  const complete = rows.value.filter((row) => row.complete)
  if (complete.length === 0) return 'The archive has no complete year to compare yet.'
  const ranked = [...complete].sort(
    (a, b) => annualValue(b, props.metric) - annualValue(a, props.metric),
  )
  const busiest = ranked[0]!
  const quietest = ranked[ranked.length - 1]!
  const median = completeYearMedian(rows.value, props.metric)
  const busiestValue = annualValue(busiest, props.metric)
  const vsMedian =
    median !== null && median > 0
      ? `, ${pctFormat.format(((busiestValue - median) / median) * 100)}% above the median year`
      : ''
  return `The busiest year was ${busiest.year} with ${describe(busiestValue)}${vsMedian}. The quietest was ${quietest.year}.`
})

const provisionalNote = computed(() => {
  const years = rows.value.filter((row) => row.provisional_months > 0).map((row) => row.year)
  if (years.length === 0) return ''
  return `Bars with a dashed outline (${years.join(', ')}) include months from the near-real-time feed. That data is not harmonized yet and adds one more VIIRS satellite, so it reads higher than archive years.`
})

const hasProvisional = computed(() => rows.value.some((row) => row.provisional_months > 0))

const partialNote = computed(() => {
  const partial = rows.value.filter((row) => !row.complete && row.total_hotspots > 0)
  if (partial.length === 0) return ''
  const list = partial.map((row) => `${row.year} (${row.months_in_archive} of 12 complete months)`)
  return `Faded bars are incomplete years in the archive: ${list.join(' and ')}. They are left out of the median.`
})

const rangeText = computed(() => {
  const range = result.value?.range
  return range ? `${range.start_year} to ${range.end_year}` : ''
})

const harmonizedMissing = computed(
  () =>
    isHarmonized.value &&
    rows.value.some((row) => row.total_hotspots > 0) &&
    rows.value.every((row) => row.harmonized_index === 0),
)

const chartDescription = computed(
  () =>
    `Bar chart of ${isHarmonized.value ? 'the harmonized index' : 'detections by sensor'} per year, ${rangeText.value}. ${summary.value}`,
)

const legend = computed(() =>
  isHarmonized.value
    ? [{ key: 'harmonized', label: 'Harmonized index', swatch: SERIES_COLORS.harmonized }]
    : [
        { key: 'modis', label: 'MODIS', swatch: SERIES_COLORS.modis },
        { key: 'viirs', label: 'VIIRS', swatch: SERIES_COLORS.viirs },
      ],
)
</script>

<template>
  <section aria-labelledby="annual-activity-title">
    <header class="border-b border-border-subtle p-5">
      <div class="max-w-[62ch]">
        <h2 id="annual-activity-title" class="text-base font-semibold text-ink-primary">
          Burning activity per year
        </h2>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Total activity for each year in the archive. The dashed line is the median of the
          complete years, so you can see which years ran above or below a typical year.
        </p>
      </div>
    </header>

    <div class="space-y-4 p-5">
      <div
        v-if="error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-100"
      >
        <span>Could not load the yearly totals. {{ error }}</span>
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
        No hotspot records are loaded for this selection yet.
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
          The database has detections but no harmonized weights yet. Load the output of the
          harmonization step, or switch to Detections.
        </p>

        <div
          :class="
            isLoading
              ? 'opacity-60 transition-opacity duration-200'
              : 'transition-opacity duration-200'
          "
        >
          <AnnualActivityChart :rows="rows" :metric="metric" :description="chartDescription" />
        </div>

        <ul class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary" aria-label="Chart legend">
          <li v-for="item in legend" :key="item.key" class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm" :style="{ backgroundColor: item.swatch }" />
            {{ item.label }}
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm bg-slate-400/35" />
            Incomplete year
          </li>
          <li v-if="hasProvisional" class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm border border-dashed border-ink-primary" />
            Near real time
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-[1.5px] border-dashed border-ink-secondary" />
            Median year
          </li>
          <li v-if="!isHarmonized" class="inline-flex items-center gap-2">
            <span class="h-3 border-l border-dotted border-accent" />
            VIIRS starts (2012)
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show yearly values</span>
            <span class="hidden group-open:inline">Hide yearly values</span>
          </summary>
          <div class="border-t border-border-subtle px-4 pb-3">
            <AnnualActivityTable :rows="rows" :metric="metric" />
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
