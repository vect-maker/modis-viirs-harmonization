<script setup lang="ts">
import { computed, watch, ref, onMounted, onUnmounted, h, render, shallowRef } from 'vue'
import { Pentagon, Trash2 } from '@lucide/vue'
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

// Vite must bundle the worker and its dependencies before MapLibre creates a map.
maplibregl.setWorkerUrl(maplibreWorkerUrl)

const props = withDefaults(
  defineProps<{
    initialCenter?: [number, number]
    initialZoom?: number
  }>(),
  {
    initialCenter: () => [-85.2072, 12.8654], // Nicaragua centroid
    initialZoom: 7,
  }
)

const emit = defineEmits<{
  (e: 'hotspot-select', hotspot: FireHotspot): void
  (e: 'roi-change', payload: { count: number; areaKm2: number | null; filtered: FireHotspot[] }): void
}>()

const mapContainer = ref<HTMLDivElement | null>(null)
const map = shallowRef<maplibregl.Map | null>(null)
const draw = shallowRef<MapboxDraw | null>(null)

const hotspotsStore = useHotspotsStore()
const { selectedSensor: selectedInstrument, filteredHotspots } = storeToRefs(hotspotsStore)
const activeRoiArea = ref<number | null>(null)
const filteredCount = computed(() => hotspotsStore.filteredHotspots.length)
const activePopup = shallowRef<maplibregl.Popup | null>(null)

const allHotspots = hotspotsStore.hotspots

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

function filterByInstrument(inst: 'ALL' | 'MODIS' | 'VIIRS') {
  hotspotsStore.setSensor(inst)
}

function startDrawPolygon() {
  const drawControl = draw.value
  if (!drawControl) return
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(drawControl as any).changeMode('draw_polygon')
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
      sources: {
        // High-resolution Esri World Imagery as the sole satellite basemap
        'esri-imagery-src': {
          type: 'raster',
          tiles: [
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          ],
          tileSize: 256,
          attribution: 'Esri, Maxar, Earthstar Geographics',
          maxzoom: 19,
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
    zoom: props.initialZoom,
    maxPitch: 60,
  })

  // Add standard navigation controls (zoom, compass)
  m.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right')

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
        'circle-radius': [
          'interpolate',
          ['linear'],
          ['zoom'],
          4,
          3.5,
          7,
          7,
          10,
          11,
          14,
          16,
        ],
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
        'circle-radius': [
          'interpolate',
          ['linear'],
          ['zoom'],
          4,
          2.5,
          7,
          4.5,
          10,
          7,
          14,
          10,
        ],
        'circle-opacity': 0.95,
        'circle-stroke-width': 1,
        'circle-stroke-color': '#ffffff',
      },
    })

    // Auto-fit bounds to frame all hotspots across Nicaragua on initial load
    if (allHotspots.length) {
      const [minX, minY, maxX, maxY] = turf.bbox(buildGeoJson(allHotspots))
      m.fitBounds(
        [[minX, minY], [maxX, maxY]],
        { padding: 50, maxZoom: 8.5, duration: 1000 },
      )
    }

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
  <div class="relative w-full h-full min-h-[550px] rounded-xl overflow-hidden shadow-2xl border border-neutral-800 bg-neutral-950">
    <!-- Map Container Target -->
    <div ref="mapContainer" class="w-full h-full min-h-[550px]" />

    <!-- Draw & Area Selection Toolbar -->
    <div class="absolute top-4 left-4 z-10 flex items-center gap-2">
      <button
        type="button"
        class="bg-neutral-900/90 hover:bg-neutral-800 text-neutral-200 hover:text-white px-3 py-1.5 rounded-lg border border-neutral-700/80 shadow-lg flex items-center gap-1.5 text-xs font-medium cursor-pointer transition backdrop-blur-md"
        @click="startDrawPolygon"
      >
        <Pentagon aria-hidden="true" class="h-3.5 w-3.5 text-neutral-300" />
        <span>Draw Area</span>
      </button>

    </div>

    <!-- Sensor Filters -->
    <div class="absolute top-4 right-14 z-10 flex flex-col gap-2">
      <!-- Sensor Filter Group -->
      <div class="bg-neutral-900/90 backdrop-blur-md p-1.5 rounded-lg border border-neutral-700/80 shadow-lg flex items-center justify-between gap-1 text-xs">
        <span class="text-[11px] text-neutral-400 font-medium px-2">Sensors:</span>
        <div class="flex items-center gap-1">
          <button
            type="button"
            :class="[
              'px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer',
              selectedInstrument === 'ALL'
                ? 'bg-neutral-700 text-white'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
            ]"
            :aria-pressed="selectedInstrument === 'ALL'"
            @click="filterByInstrument('ALL')"
          >
            All
          </button>
          <button
            type="button"
            :class="[
              'px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer flex items-center gap-1',
              selectedInstrument === 'MODIS'
                ? 'bg-neutral-700 text-white'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
            ]"
            :aria-pressed="selectedInstrument === 'MODIS'"
            @click="filterByInstrument('MODIS')"
          >
            MODIS
          </button>
          <button
            type="button"
            :class="[
              'px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer flex items-center gap-1',
              selectedInstrument === 'VIIRS'
                ? 'bg-neutral-700 text-white'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
            ]"
            :aria-pressed="selectedInstrument === 'VIIRS'"
            @click="filterByInstrument('VIIRS')"
          >
            VIIRS
          </button>
        </div>
      </div>
    </div>

    <!-- Active Area-of-Interest (ROI) Drawer Banner -->
    <div
      v-if="activeRoiArea !== null"
      class="absolute bottom-4 left-4 z-10 bg-neutral-900/95 backdrop-blur-md px-4 py-3 rounded-xl border border-orange-500/50 shadow-2xl text-xs flex flex-wrap items-center gap-4 text-neutral-200"
    >
      <div>
        <div class="flex items-center gap-2">
          <p class="font-bold text-orange-400">Selected Area</p>
        </div>
        <p class="text-[11px] text-neutral-400 mt-0.5">
          Area: <span class="font-mono text-white font-semibold">{{ activeRoiArea.toLocaleString() }} km²</span> |
          Hotspots: <span class="font-mono text-white font-semibold">{{ filteredCount.toLocaleString() }}</span>
        </p>
      </div>

      <div class="flex items-center gap-2">

        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-lg text-xs transition cursor-pointer border border-neutral-700"
          @click="clearRoi"
        >
          <Trash2 aria-hidden="true" class="h-3.5 w-3.5" />
          Clear Area
        </button>
      </div>
    </div>

    <div v-if="!filteredCount" role="status" class="pointer-events-none absolute inset-x-4 bottom-16 z-10 mx-auto max-w-sm rounded-lg border border-neutral-700 bg-neutral-900/95 p-4 text-center text-sm text-neutral-300">
      No hotspots match these filters. Try another date range, area, or sensor.
    </div>

    <!-- Map Legend -->
    <div class="absolute bottom-4 right-4 z-10 bg-neutral-900/90 backdrop-blur-md px-3 py-2 rounded-lg border border-neutral-700/80 shadow-lg text-[11px] space-y-1.5 text-neutral-300 pointer-events-none">
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-full bg-red-500 border border-white" />
        <span>Hotspots ({{ filteredCount.toLocaleString() }})</span>
      </div>
    </div>
  </div>
</template>

<style>
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
