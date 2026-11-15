<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { polygonBbox, useDiagnosticChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useChartFiltersStore } from '@/stores/chartFilters'
import BaseChartLoading from '@/components/ui/BaseChartLoading.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import SpatialDensityRenderer from '@/components/common/SpatialDensityChart.vue'

const filtersStore = useChartFiltersStore()
const { metric, activePolygon, selectedYear: storeYear } = storeToRefs(filtersStore)
const { getSpatialDensity } = useDiagnosticChartsApi()

const selectedYear = computed<number>({
  get: () => storeYear.value,
  set: (value) => filtersStore.setSelectedYear(value),
})

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

const {
  data: result,
  isLoading,
  error,
  refresh,
} = useChartLifecycle({
  fetcher: () => {
    const bbox = polygonBbox(activePolygon.value)
    return getSpatialDensity({
      cell_size_deg: cellSize.value,
      limit: 20000,
      metric: metric.value,
      start_date: `${selectedYear.value}-01-01`,
      end_date: `${selectedYear.value}-12-31`,
      ...(bbox
        ? {
            min_lat: bbox.minLat,
            max_lat: bbox.maxLat,
            min_lon: bbox.minLon,
            max_lon: bbox.maxLon,
          }
        : {}),
      polygon: activePolygon.value,
    })
  },
  watchSources: [cellSize, selectedYear, activePolygon, metric],
})

const cells = computed(() => result.value?.cells ?? [])
const topCells = computed(() => cells.value.slice(0, 20))
const isEmpty = computed(() => result.value !== null && cells.value.length === 0)
const frpFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

const summaryText = computed(() => {
  if (!result.value) return ''
  const s = result.value.summary
  const top = cells.value[0]
  if (!top) return 'No spatial cells found.'
  return `In ${selectedYear.value}, aggregated ${s.total_hotspots.toLocaleString()} detections into ${s.total_cells.toLocaleString()} grid cells (${s.cell_size_deg}°). Densest cell at (${top.cell_lat.toFixed(2)}, ${top.cell_lon.toFixed(2)}) has ${top.count.toLocaleString()} hotspots.`
})

const chartDescription = computed(
  () => `Spatial density grid scatter chart for ${selectedYear.value}. ${summaryText.value}`,
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
            Spatial hotspot density grid
          </h2>
          <span
            class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 text-[11px] text-ink-muted"
          >
            {{ activePolygon ? 'Drawn area (Polygon)' : 'All regions' }} ·
            {{ metric === 'harmonized' ? 'Harmonized' : 'Raw' }}
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          SQL grid binning (<code class="font-mono text-xs">cell_size_deg</code>) aggregating
          hotspot concentration and Fire Radiative Power across latitude and longitude.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup v-model="cellSize" :options="CELL_SIZE_OPTIONS" label="Grid resolution" />
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
          @click="refresh"
        >
          <RotateCw aria-hidden="true" class="h-3.5 w-3.5" />
          Try again
        </button>
      </div>

      <BaseChartLoading
        v-if="result === null && isLoading"
        height-class="h-[22rem]"
        label="Loading spatial density…"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No hotspot cells found for {{ selectedYear }} in this area.
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
          <SpatialDensityRenderer
            :cells="cells"
            :cell-size-deg="Number(cellSize)"
            :description="chartDescription"
          />
        </div>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show top 20 densest grid cells</span>
            <span class="hidden group-open:inline">Hide grid cell table</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[34rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Top 20 densest spatial cells
              </caption>
              <thead class="text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Cell Center (Lat, Lon)</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Detections</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Total FRP</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Avg FRP</th>
                  <th scope="col" class="py-2 text-right font-medium">Peak FRP</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="cell in topCells"
                  :key="`${cell.cell_lat}-${cell.cell_lon}`"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-mono font-medium text-ink-primary">
                    {{ cell.cell_lat.toFixed(2) }}, {{ cell.cell_lon.toFixed(2) }}
                  </th>
                  <td class="py-2 pr-4 text-right text-accent-bright">
                    {{ cell.count.toLocaleString() }}
                  </td>
                  <td class="py-2 pr-4 text-right">{{ frpFmt.format(cell.sum_frp) }} MW</td>
                  <td class="py-2 pr-4 text-right">
                    {{ cell.avg_frp !== null ? `${frpFmt.format(cell.avg_frp)} MW` : '—' }}
                  </td>
                  <td class="py-2 text-right">
                    {{ cell.max_frp !== null ? `${frpFmt.format(cell.max_frp)} MW` : '—' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
