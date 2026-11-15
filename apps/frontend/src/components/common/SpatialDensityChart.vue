<script lang="ts">
export interface SpatialDensityCell {
  cell_lat: number
  cell_lon: number
  count: number
  sum_frp: number
  avg_frp: number | null
  max_frp: number | null
}
</script>

<script setup lang="ts">
import { computed, shallowRef, useTemplateRef, watch } from 'vue'
import type { Feature, FeatureCollection, Polygon } from 'geojson'
import type * as maplibregl from 'maplibre-gl'
import { Maximize2 } from '@lucide/vue'
import { useSatelliteChartMap } from '@/composables/useSatelliteChartMap'

const SOURCE_ID = 'spatial-density-src'
const FILL_LAYER_ID = 'spatial-density-fill'

const props = defineProps<{
  cells: readonly SpatialDensityCell[]
  cellSizeDeg: number
  description: string
}>()

const mapContainer = useTemplateRef<HTMLElement>('mapContainer')
const intFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const frpFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

interface HoveredCell {
  x: number
  y: number
  cell: SpatialDensityCell
}

const hovered = shallowRef<HoveredCell | null>(null)
const maxCount = computed(() => Math.max(1, ...props.cells.map((c) => c.count)))

function toGeoJson(cells: readonly SpatialDensityCell[], cellSizeDeg: number): FeatureCollection<Polygon> {
  const half = cellSizeDeg / 2
  const logMax = Math.log10(maxCount.value + 1)

  const features: Feature<Polygon>[] = cells.map((c, index) => {
    const normCount = logMax > 0 ? Math.log10(c.count + 1) / logMax : 0.5
    return {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [c.cell_lon - half, c.cell_lat - half],
            [c.cell_lon + half, c.cell_lat - half],
            [c.cell_lon + half, c.cell_lat + half],
            [c.cell_lon - half, c.cell_lat + half],
            [c.cell_lon - half, c.cell_lat - half],
          ],
        ],
      },
      properties: {
        index,
        normCount,
      },
    }
  })

  return { type: 'FeatureCollection', features }
}

function syncSource(instance: maplibregl.Map | null) {
  if (!instance) return
  const source = instance.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined
  if (!source) return
  source.setData(toGeoJson(props.cells, props.cellSizeDeg))
  fitToCoordinates(props.cells.map((c) => [c.cell_lon, c.cell_lat]))
}

const { map, isLoaded, fitToCoordinates, resetView } = useSatelliteChartMap({
  container: mapContainer,
  onLoad(instance) {
    instance.addSource(SOURCE_ID, {
      type: 'geojson',
      data: toGeoJson(props.cells, props.cellSizeDeg),
    })

    instance.addLayer({
      id: FILL_LAYER_ID,
      type: 'fill',
      source: SOURCE_ID,
      paint: {
        'fill-color': [
          'interpolate',
          ['linear'],
          ['get', 'normCount'],
          0,
          '#2d1e3e',
          0.25,
          '#6b2d5c',
          0.5,
          '#b84a39',
          0.75,
          '#e69f00',
          1,
          '#ffe066',
        ],
        'fill-opacity': 0.8,
        'fill-outline-color': 'rgba(255, 255, 255, 0.08)',
      },
    })

    instance.on('mousemove', FILL_LAYER_ID, (e) => {
      const feature = e.features?.[0]
      const idx = feature?.properties?.index as number | undefined
      const cell = idx !== undefined ? props.cells[idx] : undefined
      if (!cell) {
        hovered.value = null
        return
      }
      instance.getCanvas().style.cursor = 'pointer'
      hovered.value = { x: e.point.x, y: e.point.y, cell }
    })

    instance.on('mouseleave', FILL_LAYER_ID, () => {
      instance.getCanvas().style.cursor = ''
      hovered.value = null
    })

    fitToCoordinates(
      props.cells.map((c) => [c.cell_lon, c.cell_lat]),
      0,
    )
  },
})

watch(
  () => [props.cells, props.cellSizeDeg] as const,
  () => {
    if (!isLoaded.value) return
    hovered.value = null
    syncSource(map.value)
  },
)

const tooltipStyle = computed(() => {
  if (!hovered.value) return {}
  const containerWidth = mapContainer.value?.clientWidth ?? 600
  const left = Math.min(Math.max(hovered.value.x + 14, 8), Math.max(8, containerWidth - 220))
  const top = Math.max(hovered.value.y - 16, 8)
  return { left: `${left}px`, top: `${top}px` }
})
</script>

<template>
  <div
    role="img"
    :aria-label="description"
    class="satellite-chart-map relative h-[32rem] w-full overflow-hidden rounded-lg border border-border-subtle bg-[#0d1117] sm:h-[38rem] lg:h-[42rem]"
  >
    <div ref="mapContainer" class="h-full w-full" aria-hidden="true" />

    <button
      type="button"
      class="absolute top-2.5 right-2.5 z-10 inline-flex items-center gap-1.5 rounded-md border border-border-strong bg-surface-panel/90 px-2.5 py-1.5 text-[11px] font-medium text-ink-secondary shadow-md backdrop-blur-sm transition-colors hover:bg-surface-elevated hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
      title="Fit map to grid cells"
      @click="resetView"
    >
      <Maximize2 class="h-3.5 w-3.5" aria-hidden="true" />
      Fit extent
    </button>

    <div
      class="pointer-events-none absolute top-1/2 right-2.5 z-10 flex -translate-y-1/2 flex-col items-center gap-1.5 rounded-md border border-border-subtle bg-surface-panel/85 px-2 py-2.5 text-[10px] text-ink-muted backdrop-blur-sm"
      aria-hidden="true"
    >
      <span class="font-medium text-ink-secondary">High</span>
      <span class="tabular-nums">{{ intFmt.format(maxCount) }}</span>
      <div
        class="h-36 w-2.5 rounded-sm border border-border-subtle"
        style="background: linear-gradient(to bottom, #ffe066, #e69f00, #b84a39, #6b2d5c, #2d1e3e)"
      />
      <span class="tabular-nums">1</span>
      <span class="font-medium text-ink-secondary">Low</span>
    </div>

    <div
      v-if="hovered"
      class="pointer-events-none absolute z-20 w-52 rounded-md border border-[#28323e] bg-[#11161d]/95 px-3 py-2 text-xs text-[#f3f4f6] shadow-lg backdrop-blur-sm"
      :style="tooltipStyle"
    >
      <div class="font-mono font-semibold">
        {{ hovered.cell.cell_lat.toFixed(2) }}°N, {{ hovered.cell.cell_lon.toFixed(2) }}°E
      </div>
      <div class="mt-0.5 text-[#ffe066]">{{ intFmt.format(hovered.cell.count) }} detections</div>
      <div class="text-[#cbd5e1]">
        Avg FRP: {{ hovered.cell.avg_frp !== null ? `${frpFmt.format(hovered.cell.avg_frp)} MW` : '—' }}
      </div>
      <div class="text-[#cbd5e1]">
        Peak FRP: {{ hovered.cell.max_frp !== null ? `${frpFmt.format(hovered.cell.max_frp)} MW` : '—' }}
      </div>
      <div class="text-[#94a3b8]">Cell size: {{ cellSizeDeg }}°</div>
    </div>

    <div
      class="pointer-events-none absolute right-2.5 bottom-2 z-10 rounded bg-surface-base/75 px-1.5 py-0.5 text-[10px] text-ink-muted"
    >
      Esri World Imagery
    </div>
  </div>
</template>
