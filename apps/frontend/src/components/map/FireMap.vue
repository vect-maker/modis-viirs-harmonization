<script setup lang="ts">
import { computed, watch, onMounted, onUnmounted, h, render, shallowRef, useTemplateRef } from 'vue'
import { useMediaQuery, usePreferredReducedMotion, useResizeObserver } from '@vueuse/core'
import * as maplibregl from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import type { MapLayerMouseEvent } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import MapboxDraw from '@mapbox/mapbox-gl-draw'
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css'
import * as turf from '@turf/turf'
import type { Feature, Point, Polygon } from 'geojson'

import type { FireHotspot } from '@/types/hotspot'
import { storeToRefs } from 'pinia'
import { useHotspotsStore } from '@/stores/hotspots'
import FirePopup from './FirePopup.vue'
import SpaceBackground from '@/components/common/SpaceBackground.vue'

// Vite must bundle the worker and its dependencies before MapLibre creates a map.
maplibregl.setWorkerUrl(maplibreWorkerUrl)

const props = withDefaults(
  defineProps<{
    initialCenter?: [number, number]
    initialZoom?: number
    sidePanelOpen?: boolean
    bottomInset?: number
  }>(),
  {
    initialCenter: () => [-85.2072, 12.8654], // Nicaragua centroid
    sidePanelOpen: false,
    bottomInset: 24,
  },
)

const emit = defineEmits<{
  (e: 'hotspot-select', hotspot: FireHotspot): void
  (
    e: 'roi-change',
    payload: { count: number; areaKm2: number | null; filtered: FireHotspot[] },
  ): void
}>()

defineSlots<{
  dock?(props: {
    drawArea: () => void
    clearArea: () => void
    resetView: () => void
    showGlobe: () => void
  }): unknown
}>()

const mapContainer = useTemplateRef<HTMLDivElement>('mapContainer')
const map = shallowRef<maplibregl.Map | null>(null)
const draw = shallowRef<MapboxDraw | null>(null)

const hotspotsStore = useHotspotsStore()
const { filteredHotspots } = storeToRefs(hotspotsStore)
const activeRoiArea = shallowRef<number | null>(null)
const filteredCount = computed(() => hotspotsStore.filteredHotspots.length)
const activePopup = shallowRef<maplibregl.Popup | null>(null)

const allHotspots = hotspotsStore.hotspots
const isDesktop = useMediaQuery('(min-width: 768px)')
const reducedMotion = usePreferredReducedMotion()
const spaceVisible = shallowRef(true)
useResizeObserver(mapContainer, () => map.value?.resize())

function getViewportPadding() {
  const height = mapContainer.value?.clientHeight ?? 600
  return {
    top: 48,
    bottom: Math.min(props.bottomInset + 48, height * 0.45),
    left: 48,
    right: isDesktop.value && props.sidePanelOpen ? 360 : 48,
  }
}

function getGlobeView() {
  const padding = getViewportPadding()
  const container = mapContainer.value
  const width = (container?.clientWidth ?? 1000) - padding.left - padding.right
  const height = (container?.clientHeight ?? 700) - padding.top - padding.bottom
  return {
    center: props.initialCenter,
    zoom: props.initialZoom ?? Math.max(0, Math.log2(Math.max(160, Math.min(width, height)) / 175)),
    bearing: 0,
    pitch: 0,
    padding,
  }
}

function showGlobe() {
  activePopup.value?.remove()
  draw.value?.changeMode('simple_select')
  map.value?.flyTo({
    ...getGlobeView(),
    duration: reducedMotion.value === 'reduce' ? 0 : 1100,
  })
}

function fitNicaragua() {
  const m = map.value
  if (!m || !allHotspots.length) return
  const [west, south, east, north] = turf.bbox(buildGeoJson(allHotspots))
  m.fitBounds(
    [
      [west, south],
      [east, north],
    ],
    {
      padding: getViewportPadding(),
      absolutePadding: true,
      bearing: 0,
      pitch: 0,
      maxZoom: 8.5,
      duration: reducedMotion.value === 'reduce' ? 0 : 700,
    },
  )
}

// Convert raw JSON data to GeoJSON Point FeatureCollection
function buildGeoJson(data: FireHotspot[]): GeoJSON.FeatureCollection<Point> {
  return {
    type: 'FeatureCollection',
    features: data.map((item, idx) => ({
      type: 'Feature',
      id: idx,
      geometry: {
        type: 'Point',
        coordinates: [item.longitude, item.latitude],
      },
      properties: { ...item },
    })),
  }
}

watch([filteredHotspots, activeRoiArea], () => {
  const source = map.value?.getSource('hotspots') as maplibregl.GeoJSONSource | undefined
  source?.setData(buildGeoJson(filteredHotspots.value))
  activePopup.value?.remove()
  emitRoiChange()
})

function startDrawPolygon() {
  const drawControl = draw.value
  if (!drawControl) return
  if ((map.value?.getZoom() ?? 0) < 5) fitNicaragua()
  drawControl.changeMode('draw_polygon')
}

function handleRoiUpdate() {
  const drawControl = draw.value
  if (!drawControl) return

  const drawnData = drawControl.getAll()
  if (!drawnData.features.length) {
    clearRoi()
    return
  }

  const polygon = drawnData.features[drawnData.features.length - 1] as Feature<Polygon>
  const areaM2 = turf.area(polygon)
  const areaKm2 = Math.round((areaM2 / 1_000_000) * 100) / 100
  activeRoiArea.value = areaKm2

  // Filter hotspots within polygon using Turf
  const matching = allHotspots.filter((h) => {
    const pt = turf.point([h.longitude, h.latitude])
    return turf.booleanPointInPolygon(pt, polygon)
  })

  hotspotsStore.setAreaHotspots(matching)
}

function emitRoiChange() {
  emit('roi-change', {
    count: filteredCount.value,
    areaKm2: activeRoiArea.value,
    filtered: hotspotsStore.filteredHotspots,
  })
}

function clearRoi() {
  const drawControl = draw.value
  if (!drawControl) return

  drawControl.deleteAll()
  activeRoiArea.value = null
  hotspotsStore.setAreaHotspots(null)
}

onMounted(() => {
  if (!mapContainer.value) return

  const m = new maplibregl.Map({
    container: mapContainer.value,
    style: {
      version: 8,
      projection: { type: 'globe' },
      sky: {
        'atmosphere-blend': 0,
      },
      sources: {
        // High-resolution Esri World Imagery as the sole satellite basemap
        'esri-imagery-src': {
          type: 'raster',
          tiles: [
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}?blankTile=false',
          ],
          tileSize: 256,
          attribution: 'Esri, Maxar, Earthstar Geographics',
          // Request real imagery; higher map zooms reuse the last available tiles.
          maxzoom: 17,
        },
      },
      layers: [
        {
          id: 'esri-imagery',
          type: 'raster',
          source: 'esri-imagery-src',
          layout: { visibility: 'visible' },
        },
      ],
    },
    center: props.initialCenter,
    zoom: props.initialZoom ?? 2,
    minZoom: 0,
    maxZoom: 17,
    maxPitch: 60,
    attributionControl: false,
  })

  // Position the globe before the first frame, leaving room for the floating panels.
  m.jumpTo(getGlobeView())
  const updateSpaceVisibility = () => {
    spaceVisible.value = m.getZoom() < 5
  }
  updateSpaceVisibility()
  m.on('zoom', updateSpaceVisibility)

  // Add standard navigation controls (zoom, compass)
  m.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-left')
  m.addControl(new maplibregl.ScaleControl({ maxWidth: 100, unit: 'metric' }), 'bottom-left')

  // Keep drawing behavior; the toolbar provides the visible controls.
  const drawControl = new MapboxDraw({
    displayControlsDefault: false,
  })
  m.addControl(drawControl as unknown as maplibregl.IControl, 'top-left')
  draw.value = drawControl

  // Listen to MapboxDraw custom events
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapWithEvents = m as any
  mapWithEvents.on('draw.create', handleRoiUpdate)
  mapWithEvents.on('draw.update', handleRoiUpdate)
  mapWithEvents.on('draw.delete', handleRoiUpdate)

  m.on('load', () => {
    const geojsonData = buildGeoJson(filteredHotspots.value)

    // Add GeoJSON active fire hotspots source
    m.addSource('hotspots', {
      type: 'geojson',
      data: geojsonData,
    })

    // Layer 1: Soft glowing heat halo underneath points
    m.addLayer({
      id: 'hotspots-glow',
      type: 'circle',
      source: 'hotspots',
      paint: {
        'circle-color': '#ef4444',
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 3.5, 7, 7, 10, 11, 14, 16],
        'circle-blur': 0.75,
        'circle-opacity': 0.65,
      },
    })

    // Layer 2: High-contrast sharp core dot on top (guaranteeing every point is distinct)
    m.addLayer({
      id: 'hotspots-circle',
      type: 'circle',
      source: 'hotspots',
      paint: {
        'circle-color': '#ef4444',
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 2.5, 7, 4.5, 10, 7, 14, 10],
        'circle-opacity': 0.95,
        'circle-stroke-width': 1,
        'circle-stroke-color': '#ffffff',
      },
    })

    // Cursor pointer on hover
    m.on('mouseenter', 'hotspots-circle', () => {
      m.getCanvas().style.cursor = 'pointer'
    })
    m.on('mouseleave', 'hotspots-circle', () => {
      m.getCanvas().style.cursor = ''
    })

    // Hotspot click: Mount reactive Vue FirePopup into MapLibre popup
    m.on('click', 'hotspots-circle', (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0]
      if (!feature) return

      const coordinates = (feature.geometry as Point).coordinates.slice() as [number, number]
      const hotspotProps = feature.properties as FireHotspot

      const popupWrapper = document.createElement('div')
      const vnode = h(FirePopup, {
        hotspot: hotspotProps,
        onSelect: (hSpot) => {
          emit('hotspot-select', hSpot)
        },
      })
      render(vnode, popupWrapper)

      activePopup.value?.remove()
      activePopup.value = new maplibregl.Popup({ offset: 12, maxWidth: '280px' })
        .setLngLat(coordinates)
        .setDOMContent(popupWrapper)
        .addTo(m)
      activePopup.value.on('close', () => render(null, popupWrapper))
    })
  })

  map.value = m
})

onUnmounted(() => {
  activePopup.value?.remove()
  map.value?.remove()
})
</script>

<template>
  <div
    class="fire-map relative h-full w-full overflow-hidden bg-neutral-950"
    :style="{ '--map-bottom-inset': `${bottomInset + 8}px` }"
  >
    <SpaceBackground :visible="spaceVisible" />
    <div ref="mapContainer" class="fire-map__canvas" />

    <slot
      name="dock"
      :draw-area="startDrawPolygon"
      :clear-area="clearRoi"
      :reset-view="fitNicaragua"
      :show-globe="showGlobe"
    />

    <div
      v-if="!filteredCount"
      role="status"
      :style="{ bottom: `${bottomInset + 80}px` }"
      class="pointer-events-none absolute inset-x-4 z-10 mx-auto max-w-sm rounded-lg border border-white/10 bg-neutral-950/95 p-4 text-center text-sm text-neutral-300"
    >
      No hotspots match these filters. Try another date range, area, or sensor.
    </div>
  </div>
</template>

<style>
.fire-map {
  background-color: #020409;
}

/* MapLibre's unlayered position: relative overrides Tailwind's absolute utility.
   Explicit dimensions keep the canvas sized to the full map workspace. */
.fire-map > .fire-map__canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  background: transparent;
}
.fire-map .maplibregl-ctrl-top-left {
  top: 0.75rem;
  left: 0.75rem;
}
.fire-map .maplibregl-ctrl-top-left .maplibregl-ctrl {
  margin: 0;
}
.fire-map .maplibregl-ctrl-group {
  overflow: hidden;
  border: 1px solid #ffffff26;
  border-radius: 0.625rem;
  background: #0a0a0aeb;
  box-shadow: 0 4px 12px #0004;
}
.fire-map .maplibregl-ctrl-group button {
  width: 36px;
  height: 36px;
}
.fire-map .maplibregl-ctrl-group button:hover {
  background-color: #262626;
}
.fire-map .maplibregl-ctrl-group button + button {
  border-top-color: #ffffff1a;
}
.fire-map .maplibregl-ctrl-icon {
  filter: invert(1);
}
.fire-map .maplibregl-ctrl-bottom-left {
  bottom: var(--map-bottom-inset);
}
.fire-map .maplibregl-ctrl-scale {
  border-color: #ffffff99;
  background: #0a0a0abf;
  color: #e5e5e5;
  font-size: 10px;
}

/* Custom overrides for MapLibre Popups to match dark theme */
.maplibregl-popup-content {
  background: transparent !important;
  padding: 0 !important;
  box-shadow: none !important;
}

.maplibregl-popup-anchor-top .maplibregl-popup-tip {
  border-bottom-color: #171717 !important;
}
.maplibregl-popup-anchor-bottom .maplibregl-popup-tip {
  border-top-color: #171717 !important;
}
.maplibregl-popup-anchor-left .maplibregl-popup-tip {
  border-right-color: #171717 !important;
}
.maplibregl-popup-anchor-right .maplibregl-popup-tip {
  border-left-color: #171717 !important;
}
.maplibregl-popup-close-button {
  color: #a3a3a3 !important;
  padding: 4px 8px !important;
  font-size: 16px !important;
}
.maplibregl-popup-close-button:hover {
  color: #ffffff !important;
  background: transparent !important;
}
</style>
