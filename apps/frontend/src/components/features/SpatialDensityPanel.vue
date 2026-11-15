<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useApiFetch } from '@/api/useApiFetch'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import SpatialDensityChart from '@/components/common/SpatialDensityChart.vue'

const props = defineProps<{
  polygon: GeoJSONPolygon | null
  metric?: 'raw' | 'harmonized'
}>()

const selectedYear = defineModel<number>('year', { default: 2025 })

const ResponseSchema = z.object({
  summary: z.object({
    cell_size_deg: z.number(),
    total_cells: z.number().int().nonnegative(),
    total_hotspots: z.number().int().nonnegative(),
    cell_count_stats: z.object({
      count: z.number().int().nonnegative(),
      mean: z.number().nullable(),
      median: z.number().nullable(),
      p90: z.number().nullable(),
      max: z.number().nullable(),
    }),
  }),
  data: z.array(
    z.object({
      cell_lat: z.number(),
      cell_lon: z.number(),
      count: z.number().int().nonnegative(),
      sum_frp: z.number(),
      avg_frp: z.number().nullable(),
      max_frp: z.number().nullable(),
    }),
  ),
})
type SpatialDensityResponse = z.infer<typeof ResponseSchema>

const CELL_SIZE_OPTIONS = [
  { value: '0.05', label: '0.05° (~5.5 km)' },
  { value: '0.1', label: '0.10° (~11 km)' },
  { value: '0.25', label: '0.25° (~28 km)' },
  { value: '0.5', label: '0.50° (~55 km)' },
] as const

const YEAR_OPTIONS = Array.from({ length: 26 }, (_, idx) => {
  const year = 2026 - idx
  return { value: year, label: String(year) }
})

const cellSize = shallowRef<'0.05' | '0.1' | '0.25' | '0.5'>('0.1')
const result = shallowRef<SpatialDensityResponse | null>(null)
const isLoading = shallowRef(false)
const error = shallowRef<string | null>(null)
let latestRequest = 0

function polygonBbox(polygon: GeoJSONPolygon | null) {
  if (!polygon) return null
  const ring = polygon.coordinates[0]
  if (!ring || ring.length === 0) return null
  let minLon = Infinity
  let maxLon = -Infinity
  let minLat = Infinity
  let maxLat = -Infinity
  for (const pt of ring) {
    const lon = pt[0]
    const lat = pt[1]
    if (lon === undefined || lat === undefined) continue
    if (lon < minLon) minLon = lon
    if (lon > maxLon) maxLon = lon
    if (lat < minLat) minLat = lat
    if (lat > maxLat) maxLat = lat
  }
  return Number.isFinite(minLat) ? { minLat, maxLat, minLon, maxLon } : null
}

async function load() {
  const requestId = ++latestRequest
  isLoading.value = true
  error.value = null

  // Usamos limit=20000 (máximo permitido por el backend) para evitar truncar celdas y totales anuales.
  const params = new URLSearchParams({
    cell_size_deg: cellSize.value,
    limit: '20000',
    metric: props.metric ?? 'raw',
    start_date: `${selectedYear.value}-01-01T00:00:00`,
    end_date: `${selectedYear.value}-12-31T23:59:59`,
  })
  const bbox = polygonBbox(props.polygon)
  if (bbox) {
    params.set('min_lat', String(bbox.minLat))
    params.set('max_lat', String(bbox.maxLat))
    params.set('min_lon', String(bbox.minLon))
    params.set('max_lon', String(bbox.maxLon))
  }
  if (props.polygon) {
    params.set('polygon', JSON.stringify(props.polygon))
  }

  const { data, error: fetchError } = await useApiFetch(
    `/dashboard/spatial-density?${params.toString()}`,
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

watch([cellSize, selectedYear, () => props.polygon, () => props.metric], load, { immediate: true })

const cells = computed(() => result.value?.data ?? [])
const topCells = computed(() => cells.value.slice(0, 20))
const isEmpty = computed(() => result.value !== null && cells.value.length === 0)
const frpFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

const summaryText = computed(() => {
  if (!result.value || cells.value.length === 0) return ''
  const s = result.value.summary
  const top = cells.value[0]!
  return `In ${selectedYear.value}, aggregated ${s.total_hotspots.toLocaleString()} raw detections across ${s.total_cells.toLocaleString()} grid cells (${s.cell_size_deg}° resolution). Peak cell at (${top.cell_lat.toFixed(2)}°N, ${top.cell_lon.toFixed(2)}°E) holds ${top.count.toLocaleString()} detections.`
})

const chartDescription = computed(
  () => `Spatial grid density scatter plot for ${selectedYear.value}. ${summaryText.value}`,
)
</script>

<template>
  <section aria-labelledby="spatial-density-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="spatial-density-title" class="text-base font-semibold text-ink-primary">
            Spatial grid density (SQL binning)
          </h2>
          <span
            class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 text-[11px] text-ink-muted"
          >
            {{ polygon ? 'Drawn area (Polygon)' : 'All regions' }} ·
            {{ metric === 'harmonized' ? 'Harmonized index' : 'Raw detections' }}
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Groups detections into regular latitude/longitude cells in SQL as a fast alternative to
          client-side hexbinning, reporting counts and radiative power per cell.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup v-model="cellSize" :options="CELL_SIZE_OPTIONS" label="Grid cell size" />
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
        <span>Could not load spatial density. {{ error }}</span>
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
        class="h-[32rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse sm:h-[38rem] lg:h-[42rem]"
        aria-hidden="true"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No grid cells with detections found for this area and period.
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
          <SpatialDensityChart
            :cells="cells"
            :cell-size-deg="result.summary.cell_size_deg"
            :description="chartDescription"
          />
        </div>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show top 20 densest cells</span>
            <span class="hidden group-open:inline">Hide top 20 densest cells</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[34rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Top 20 spatial grid cells by hotspot count
              </caption>
              <thead class="text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Cell Center (Lat, Lon)</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Hotspots</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Avg FRP</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Max FRP</th>
                  <th scope="col" class="py-2 text-right font-medium">Sum FRP</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="cell in topCells"
                  :key="`${cell.cell_lat}-${cell.cell_lon}`"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-mono font-medium text-ink-primary">
                    {{ cell.cell_lat.toFixed(3) }}°, {{ cell.cell_lon.toFixed(3) }}°
                  </th>
                  <td class="py-2 pr-4 text-right text-accent-bright">
                    {{ cell.count.toLocaleString() }}
                  </td>
                  <td class="py-2 pr-4 text-right">
                    {{ cell.avg_frp !== null ? `${frpFmt.format(cell.avg_frp)} MW` : '—' }}
                  </td>
                  <td class="py-2 pr-4 text-right">
                    {{ cell.max_frp !== null ? `${frpFmt.format(cell.max_frp)} MW` : '—' }}
                  </td>
                  <td class="py-2 text-right">{{ frpFmt.format(cell.sum_frp) }} MW</td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
