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
import { GeoJSONPolygonSchema } from 'zod-geojson'

import type { HotspotResponse } from '@/api'
import { Flame } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { useHotspotsStore } from '@/stores/hotspots'
import FirePopup from './FirePopup.vue'
import MapLegendTooltip from './MapLegendTooltip.vue'
import UserLocationMarker from './UserLocationMarker.vue'
import SpaceBackground from '@/components/common/SpaceBackground.vue'
import { getMapColors } from '@/utils/themeColors'

// Vite must bundle the worker and its dependencies before MapLibre creates a map.
maplibregl.setWorkerUrl(maplibreWorkerUrl)

const props = withDefaults(
  defineProps<{
    initialCenter?: [number, number]
    initialZoom?: number
    sidePanelOpen?: boolean
    bottomInset?: number
    userLocation?: { latitude: number; longitude: number } | null
  }>(),
  {
    initialCenter: () => [-85.2072, 12.8654], // Nicaragua centroid
    sidePanelOpen: false,
    bottomInset: 24,
    userLocation: null,
  },
)

const emit = defineEmits<{
  (
    e: 'roi-change',
    payload: { count: number; areaKm2: number | null; filtered: HotspotResponse[] },
  ): void
  (e: 'request-location'): void
}>()

defineSlots<{
  dock?(props: {
    drawArea: () => void
    confirmDraw: () => void
    cancelDraw: () => void
    clearArea: () => void
    locateUser: () => void
    showGlobe: () => void
    isDrawing: boolean
  }): unknown
}>()

const mapContainer = useTemplateRef<HTMLDivElement>('mapContainer')
const map = shallowRef<maplibregl.Map | null>(null)
const draw = shallowRef<MapboxDraw | null>(null)

const hotspotsStore = useHotspotsStore()
const { filteredHotspots } = storeToRefs(hotspotsStore)
const activeRoiArea = shallowRef<number | null>(null)
const isDrawing = shallowRef(false)
const filteredCount = computed(() => hotspotsStore.filteredHotspots.length)
const activePopup = shallowRef<maplibregl.Popup | null>(null)

const isDesktop = useMediaQuery('(min-width: 768px)')
const reducedMotion = usePreferredReducedMotion()
const spaceVisible = shallowRef(true)
useResizeObserver(mapContainer, () => map.value?.resize())
const userMarker = shallowRef<maplibregl.Marker | null>(null)
const userMarkerContainer = shallowRef<HTMLDivElement | null>(null)

function flyToCoords(longitude: number, latitude: number) {
  activePopup.value?.remove()
  draw.value?.changeMode('simple_select')
  map.value?.flyTo({
    center: [longitude, latitude],
    zoom: 9,
    bearing: 0,
    pitch: 0,
    padding: getViewportPadding(),
    duration: reducedMotion.value === 'reduce' ? 0 : 900,
  })
}

function createUserMarkerElement(): HTMLDivElement {
  const wrapper = document.createElement('div')
  render(h(UserLocationMarker), wrapper)
  userMarkerContainer.value = wrapper
  return wrapper
}

function removeUserMarker() {
  userMarker.value?.remove()
  userMarker.value = null
  if (userMarkerContainer.value) {
    render(null, userMarkerContainer.value)
    userMarkerContainer.value = null
  }
}

function syncUserMarker() {
  const m = map.value
  const loc = props.userLocation
  if (!m || !loc) {
    removeUserMarker()
    return
  }

  if (!userMarker.value) {
    userMarker.value = new maplibregl.Marker({ element: createUserMarkerElement() })
      .setLngLat([loc.longitude, loc.latitude])
      .addTo(m)
    return
  }

  userMarker.value.setLngLat([loc.longitude, loc.latitude])
}

watch([map, () => props.userLocation], syncUserMarker)

function locateUser() {
  if (props.userLocation) {
    flyToCoords(props.userLocation.longitude, props.userLocation.latitude)
    return
  }
  emit('request-location')
}

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
  const currentHotspots = hotspotsStore.hotspots
  if (!m || !currentHotspots.length) return
  const [west, south, east, north] = turf.bbox(buildGeoJson(currentHotspots))
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

// Convert API hotspot records to GeoJSON Point FeatureCollection
function buildGeoJson(data: HotspotResponse[]): GeoJSON.FeatureCollection<Point> {
  return {
    type: 'FeatureCollection',
    features: data.map((item, idx) => ({
      type: 'Feature',
      id: idx,
      geometry: {
        type: 'Point',
        coordinates: [item.longitude, item.latitude],
      },
      properties: {
        ...item,
        confidence_class: (item.confidence_class ?? 'unknown').toLowerCase(),
      },
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
  isDrawing.value = true
  drawControl.changeMode('draw_polygon')
}

function confirmDrawPolygon() {
  const drawControl = draw.value
  if (!drawControl) return
  drawControl.changeMode('simple_select')
  isDrawing.value = false
  handleRoiUpdate()
}

function cancelDrawPolygon() {
  const drawControl = draw.value
  if (!drawControl) return
  drawControl.trash()
  drawControl.changeMode('simple_select')
  isDrawing.value = false
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
  const validatedPolygon = GeoJSONPolygonSchema.parse(polygon.geometry)
  const areaM2 = turf.area(polygon)
  const areaKm2 = Math.round((areaM2 / 1_000_000) * 100) / 100
  activeRoiArea.value = areaKm2

  void hotspotsStore.setSelectedPolygon(validatedPolygon)
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
  void hotspotsStore.setSelectedPolygon(null)
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
  mapWithEvents.on('draw.modechange', (event: { mode: string }) => {
    isDrawing.value = event.mode === 'draw_polygon'
  })

  m.on('load', () => {
    const geojsonData = buildGeoJson(filteredHotspots.value)
    const mapColors = getMapColors()

    // Add GeoJSON active fire hotspots source
    m.addSource('hotspots', {
      type: 'geojson',
      data: geojsonData,
    })

    // Layer 1: Soft glowing heat halo underneath points (colored by confidence)
    m.addLayer({
      id: 'hotspots-glow',
      type: 'circle',
      source: 'hotspots',
      paint: {
        'circle-color': [
          'match',
          ['get', 'confidence_class'],
          'high',
          '#ef4444',
          'nominal',
          '#f97316',
          'low',
          '#eab308',
          '#94a3b8',
        ],
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 3.5, 7, 7, 10, 11, 14, 16],
        'circle-blur': 0.75,
        'circle-opacity': 0.65,
      },
    })

    // Layer 2: Confidence-coded Lucide Flame icons on top of the heat halo
    const confidenceStyles = [
      { id: 'hotspot-flame-high', fill: '#ef4444', stroke: '#fef08a' },
      { id: 'hotspot-flame-nominal', fill: '#f97316', stroke: '#fed7aa' },
      { id: 'hotspot-flame-low', fill: '#eab308', stroke: '#fef9c3' },
      { id: 'hotspot-flame-unknown', fill: '#94a3b8', stroke: '#e2e8f0' },
    ] as const

    let loadedIcons = 0
    const ensureSymbolLayer = () => {
      if (!map.value || m.getLayer('hotspots-symbol')) return
      m.addLayer({
        id: 'hotspots-symbol',
        type: 'symbol',
        source: 'hotspots',
        layout: {
          'icon-image': [
            'match',
            ['get', 'confidence_class'],
            'high',
            'hotspot-flame-high',
            'nominal',
            'hotspot-flame-nominal',
            'low',
            'hotspot-flame-low',
            'hotspot-flame-unknown',
          ],
          'icon-size': ['interpolate', ['linear'], ['zoom'], 4, 0.55, 7, 0.75, 10, 1.0, 14, 1.25],
          'icon-allow-overlap': true,
          'icon-anchor': 'bottom',
        },
      })
    }

    for (const style of confidenceStyles) {
      const svgHost = document.createElement('div')
      render(
        h(Flame, {
          size: 44,
          strokeWidth: 2,
          color: style.stroke,
          fill: style.fill,
        }),
        svgHost,
      )
      const svgEl = svgHost.querySelector('svg')
      if (!svgEl) {
        render(null, svgHost)
        continue
      }
      svgEl.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
      const svgMarkup = new XMLSerializer().serializeToString(svgEl)
      render(null, svgHost)

      const img = new Image(44, 44)
      img.onload = () => {
        if (!map.value) return
        if (!m.hasImage(style.id)) {
          m.addImage(style.id, img, { pixelRatio: 2 })
        }
        loadedIcons += 1
        if (loadedIcons === confidenceStyles.length) {
          ensureSymbolLayer()
        }
      }
      img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgMarkup)}`
    }

    // Cursor pointer on hover
    m.on('mouseenter', 'hotspots-symbol', () => {
      m.getCanvas().style.cursor = 'pointer'
    })
    m.on('mouseleave', 'hotspots-symbol', () => {
      m.getCanvas().style.cursor = ''
    })

    // Hotspot click: Mount reactive Vue FirePopup into MapLibre popup
    m.on('click', 'hotspots-symbol', (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0]
      if (!feature) return

      const coordinates = (feature.geometry as Point).coordinates.slice() as [number, number]
      const featureId = feature.properties?.id as string | undefined
      const hotspot =
        (featureId
          ? filteredHotspots.value.find((item) => item.id === featureId)
          : undefined) ?? (feature.properties as HotspotResponse)

      const popupWrapper = document.createElement('div')
      const vnode = h(FirePopup, {
        hotspot,
        platform: hotspotsStore.getPlatform(hotspot.platform_id),
        country: hotspotsStore.getCountry(hotspot.country_id),
      })
      render(vnode, popupWrapper)

      activePopup.value?.remove()
      activePopup.value = new maplibregl.Popup({ offset: 14, maxWidth: '310px' })
        .setLngLat(coordinates)
        .setDOMContent(popupWrapper)
        .addTo(m)
      activePopup.value.on('close', () => render(null, popupWrapper))
    })
  })

  map.value = m
})

onUnmounted(() => {
  removeUserMarker()
  activePopup.value?.remove()
  map.value?.remove()
})
</script>

<template>
  <div
    class="fire-map relative h-full w-full overflow-hidden bg-surface-base"
    :style="{ '--map-bottom-inset': `${bottomInset + 8}px` }"
  >
    <SpaceBackground :visible="spaceVisible" />
    <div ref="mapContainer" class="fire-map__canvas" />

    <div class="absolute top-3 left-13 z-10">
      <MapLegendTooltip />
    </div>

    <slot
      name="dock"
      :draw-area="startDrawPolygon"
      :confirm-draw="confirmDrawPolygon"
      :cancel-draw="cancelDrawPolygon"
      :clear-area="clearRoi"
      :locate-user="locateUser"
      :show-globe="showGlobe"
      :is-drawing="isDrawing"
    />

    <div
      v-if="!filteredCount"
      role="status"
      :style="{ bottom: `${bottomInset + 80}px` }"
      class="pointer-events-none absolute inset-x-4 z-10 mx-auto max-w-sm rounded-lg border border-border-subtle bg-surface-panel/95 p-4 text-center text-sm text-ink-secondary"
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
  border: 1px solid var(--color-border-strong);
  border-radius: 0.625rem;
  background: color-mix(in srgb, var(--color-surface-panel) 92%, transparent);
  box-shadow: 0 4px 12px #0004;
}
.fire-map .maplibregl-ctrl-group button {
  width: 36px;
  height: 36px;
}
.fire-map .maplibregl-ctrl-group button:hover {
  background-color: var(--color-surface-elevated);
}
.fire-map .maplibregl-ctrl-group button + button {
  border-top-color: var(--color-border-subtle);
}
.fire-map .maplibregl-ctrl-icon {
  filter: invert(1);
}
.fire-map .maplibregl-ctrl-bottom-left {
  bottom: var(--map-bottom-inset);
}
.fire-map .maplibregl-ctrl-scale {
  border-color: var(--color-border-strong);
  background: color-mix(in srgb, var(--color-surface-panel) 85%, transparent);
  color: var(--color-ink-secondary);
  font-size: 10px;
}

/* Custom overrides for MapLibre Popups to match dark theme */
.maplibregl-popup-content {
  background: transparent !important;
  padding: 0 !important;
  box-shadow: none !important;
}

.maplibregl-popup-anchor-top .maplibregl-popup-tip {
  border-bottom-color: var(--color-surface-panel) !important;
}
.maplibregl-popup-anchor-bottom .maplibregl-popup-tip {
  border-top-color: var(--color-surface-panel) !important;
}
.maplibregl-popup-anchor-left .maplibregl-popup-tip {
  border-right-color: var(--color-surface-panel) !important;
}
.maplibregl-popup-anchor-right .maplibregl-popup-tip {
  border-left-color: var(--color-surface-panel) !important;
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
