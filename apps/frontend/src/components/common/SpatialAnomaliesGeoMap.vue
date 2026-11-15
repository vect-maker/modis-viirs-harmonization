<script setup lang="ts">
import { computed, shallowRef, useTemplateRef, watch } from 'vue'
import type { Feature, FeatureCollection, Point } from 'geojson'
import type * as maplibregl from 'maplibre-gl'
import { Maximize2 } from '@lucide/vue'
import { useSatelliteChartMap } from '@/composables/useSatelliteChartMap'
import type { SpatialAnomalyPoint } from './SpatialAnomaliesChart.vue'

const SOURCE_ID = 'spatial-anomalies-src'
const NORMAL_LAYER_ID = 'spatial-anomalies-normal'
const OUTLIER_LAYER_ID = 'spatial-anomalies-outliers'

const props = defineProps<{
  points: readonly SpatialAnomalyPoint[]
  description: string
}>()

const mapContainer = useTemplateRef<HTMLElement>('mapContainer')
const frpFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

interface HoveredAnomaly {
  x: number
  y: number
  pt: SpatialAnomalyPoint
}

const hovered = shallowRef<HoveredAnomaly | null>(null)

function toGeoJson(points: readonly SpatialAnomalyPoint[]): FeatureCollection<Point> {
  const features: Feature<Point>[] = points.map((pt, index) => ({
    type: 'Feature',
    geometry: {
      type: 'Point',
      coordinates: [pt.longitude, pt.latitude],
    },
    properties: {
      index,
      is_anomaly: pt.is_anomaly,
    },
  }))
  return { type: 'FeatureCollection', features }
}

function syncSource(instance: maplibregl.Map | null) {
  if (!instance) return
  const source = instance.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined
  if (!source) return
  source.setData(toGeoJson(props.points))
  fitToCoordinates(props.points.map((p) => [p.longitude, p.latitude]))
}

const { map, isLoaded, fitToCoordinates, resetView } = useSatelliteChartMap({
  container: mapContainer,
  onLoad(instance) {
    instance.addSource(SOURCE_ID, {
      type: 'geojson',
      data: toGeoJson(props.points),
    })

    instance.addLayer({
      id: NORMAL_LAYER_ID,
      type: 'circle',
      source: SOURCE_ID,
      filter: ['!', ['get', 'is_anomaly']],
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 2.2, 8, 3.5, 12, 5],
        'circle-color': '#94a3b8',
        'circle-opacity': 0.5,
      },
    })

    instance.addLayer({
      id: OUTLIER_LAYER_ID,
      type: 'circle',
      source: SOURCE_ID,
      filter: ['==', ['get', 'is_anomaly'], true],
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 3.5, 8, 5, 12, 7],
        'circle-color': '#e69f00',
        'circle-stroke-color': '#ffe066',
        'circle-stroke-width': 1.1,
        'circle-opacity': 0.95,
      },
    })

    const interactiveLayers = [OUTLIER_LAYER_ID, NORMAL_LAYER_ID]

    instance.on('mousemove', interactiveLayers, (e) => {
      const feature = e.features?.[0]
      const idx = feature?.properties?.index as number | undefined
      const pt = idx !== undefined ? props.points[idx] : undefined
      if (!pt) {
        hovered.value = null
        return
      }
      instance.getCanvas().style.cursor = 'pointer'
      hovered.value = { x: e.point.x, y: e.point.y, pt }
    })

    instance.on('mouseleave', interactiveLayers, () => {
      instance.getCanvas().style.cursor = ''
      hovered.value = null
    })

    fitToCoordinates(
      props.points.map((p) => [p.longitude, p.latitude]),
      0,
    )
  },
})

watch(
  () => props.points,
  () => {
    if (!isLoaded.value) return
    hovered.value = null
    syncSource(map.value)
  },
)

const tooltipStyle = computed(() => {
  if (!hovered.value) return {}
  const containerWidth = mapContainer.value?.clientWidth ?? 600
  const left = Math.min(Math.max(hovered.value.x + 14, 8), Math.max(8, containerWidth - 240))
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
      title="Fit map to detections"
      @click="resetView"
    >
      <Maximize2 class="h-3.5 w-3.5" aria-hidden="true" />
      Fit extent
    </button>

    <div
      v-if="hovered"
      class="pointer-events-none absolute z-20 w-56 rounded-md border border-[#28323e] bg-[#11161d]/95 px-3 py-2 text-xs text-[#f3f4f6] shadow-lg backdrop-blur-sm"
      :style="tooltipStyle"
    >
      <div
        class="font-semibold"
        :class="hovered.pt.is_anomaly ? 'text-[#ffe066]' : 'text-[#cbd5e1]'"
      >
        {{ hovered.pt.is_anomaly ? 'Spatial Anomaly (Outlier)' : 'Normal Cluster Point' }}
      </div>
      <div class="mt-0.5 font-mono text-[#f3f4f6]">
        {{ hovered.pt.latitude.toFixed(4) }}°N, {{ hovered.pt.longitude.toFixed(4) }}°E
      </div>
      <div class="text-[#cbd5e1]">Decision score: {{ hovered.pt.score.toFixed(4) }}</div>
      <div class="text-[#cbd5e1]">
        FRP: {{ hovered.pt.frp !== null ? `${frpFmt.format(hovered.pt.frp)} MW` : '—' }}
      </div>
      <div class="text-[#94a3b8]">
        {{ hovered.pt.acq_datetime ? `${hovered.pt.acq_datetime.slice(0, 19)} UTC` : '—' }}
      </div>
    </div>

    <div
      class="pointer-events-none absolute right-2.5 bottom-2 z-10 rounded bg-surface-base/75 px-1.5 py-0.5 text-[10px] text-ink-muted"
    >
      Esri World Imagery
    </div>
  </div>
</template>
