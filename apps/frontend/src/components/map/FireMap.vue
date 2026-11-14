<script setup lang="ts">
import { ref, onMounted, onUnmounted, h, render, shallowRef } from 'vue'
import * as maplibregl from 'maplibre-gl'
import type { MapLayerMouseEvent } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import MapboxDraw from '@mapbox/mapbox-gl-draw'
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css'
import * as turf from '@turf/turf'
import type { Feature, Point, Polygon } from 'geojson'

import type { FireHotspot } from '@/types/hotspot'
import rawHotspots from '@/data/sample_hotspots.json'
import FirePopup from './FirePopup.vue'

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

const selectedInstrument = ref<'ALL' | 'MODIS' | 'VIIRS'>('ALL')
const activeRoiArea = ref<number | null>(null)
const filteredCount = ref<number>(rawHotspots.length)
const lastPolygon = shallowRef<Feature<Polygon> | null>(null)
const currentMatching = shallowRef<FireHotspot[]>(rawHotspots as FireHotspot[])
const hasConsulted = ref(false)

const allHotspots = rawHotspots as FireHotspot[]

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

function filterByInstrument(inst: 'ALL' | 'MODIS' | 'VIIRS') {
  selectedInstrument.value = inst
  const m = map.value
  if (!m) return

  const filterExpr =
    inst === 'ALL'
      ? null
      : (['==', ['get', 'instrument'], inst] as unknown as maplibregl.FilterSpecification)
  if (m.getLayer('hotspots-glow')) {
    m.setFilter('hotspots-glow', filterExpr)
  }
  if (m.getLayer('hotspots-circle')) {
    m.setFilter('hotspots-circle', filterExpr)
  }
}

function startDrawPolygon() {
  const drawControl = draw.value
  if (!drawControl) return
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(drawControl as any).changeMode('draw_polygon')
}

function consultRoi() {
  if (!lastPolygon.value) return
  const polygon = lastPolygon.value
  const bbox = turf.bbox(polygon)
  const matching = currentMatching.value

  console.group('%c🔥 [FIRMS Spatial Query - Area of Interest Consulted]', 'color: #f97316; font-weight: bold; font-size: 13px;')
  console.log('%cSelected Polygon GeoJSON:', 'color: #38bdf8; font-weight: bold;', polygon)
  console.log('%cBounding Box [west, south, east, north]:', 'color: #38bdf8; font-weight: bold;', bbox)
  console.log('%cCalculated Area:', 'color: #38bdf8; font-weight: bold;', `${activeRoiArea.value?.toLocaleString()} km²`)
  console.log('%cMatching Active Fire Hotspots:', 'color: #4ade80; font-weight: bold;', matching.length)
  console.log('%cFull API Query Payload:', 'color: #fb923c; font-weight: bold;', {
    type: 'Feature',
    geometry: polygon.geometry,
    bbox,
    properties: {
      areaKm2: activeRoiArea.value,
      hotspotCount: matching.length,
      sensors: ['MODIS', 'VIIRS'],
    },
    sampleHotspots: matching.slice(0, 50),
  })
  console.groupEnd()

  hasConsulted.value = true
  setTimeout(() => {
    hasConsulted.value = false
  }, 3500)
}

function handleRoiUpdate() {
  const drawControl = draw.value
  if (!drawControl) return

  const drawnData = drawControl.getAll()
  if (!drawnData.features.length) {
    activeRoiArea.value = null
    lastPolygon.value = null
    currentMatching.value = allHotspots
    filteredCount.value = allHotspots.length
    emit('roi-change', { count: allHotspots.length, areaKm2: null, filtered: allHotspots })
    return
  }

  const polygon = drawnData.features[drawnData.features.length - 1] as Feature<Polygon>
  lastPolygon.value = polygon
  const areaM2 = turf.area(polygon)
  const areaKm2 = Math.round((areaM2 / 1_000_000) * 100) / 100
  activeRoiArea.value = areaKm2

  // Filter hotspots within polygon using Turf
  const matching = allHotspots.filter((h) => {
    const pt = turf.point([h.longitude, h.latitude])
    return turf.booleanPointInPolygon(pt, polygon)
  })

  currentMatching.value = matching
  filteredCount.value = matching.length
  emit('roi-change', { count: matching.length, areaKm2, filtered: matching })

  // Automatically log immediate feedback to console
  console.log(
    `%c[FIRMS Draw] Area updated: ${areaKm2} km² | Hotspots matched: ${matching.length}`,
    'color: #f97316;'
  )

  // Update map source with ROI subset
  const source = map.value?.getSource('hotspots') as maplibregl.GeoJSONSource | undefined
  if (source) {
    source.setData(buildGeoJson(matching))
  }
}

function clearRoi() {
  const drawControl = draw.value
  if (!drawControl) return

  drawControl.deleteAll()
  activeRoiArea.value = null
  lastPolygon.value = null
  currentMatching.value = allHotspots
  filteredCount.value = allHotspots.length

  const source = map.value?.getSource('hotspots') as maplibregl.GeoJSONSource | undefined
  if (source) {
    source.setData(buildGeoJson(allHotspots))
  }
  emit('roi-change', { count: allHotspots.length, areaKm2: null, filtered: allHotspots })
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

  // Add drawing controls (Polygon, Trash) for Area of Interest (ROI) selection
  const drawControl = new MapboxDraw({
    displayControlsDefault: false,
    controls: {
      polygon: true,
      trash: true,
    },
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
    const geojsonData = buildGeoJson(allHotspots)

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
        'circle-color': [
          'match',
          ['get', 'instrument'],
          'MODIS',
          '#ff1a1a', // Fiery crimson glow
          'VIIRS',
          '#ff9900', // Fiery amber glow
          '#ff6600',
        ],
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
        'circle-color': [
          'match',
          ['get', 'instrument'],
          'MODIS',
          '#ef233c', // Vivid MODIS red
          'VIIRS',
          '#ffd166', // Bright VIIRS gold/yellow
          '#ff9f1c',
        ],
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
    const [minX, minY, maxX, maxY] = turf.bbox(geojsonData)
    m.fitBounds(
      [
        [minX, minY],
        [maxX, maxY],
      ],
      {
        padding: 50,
        maxZoom: 8.5,
        duration: 1000,
      }
    )

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

      new maplibregl.Popup({ offset: 12, maxWidth: '280px' })
        .setLngLat(coordinates)
        .setDOMContent(popupWrapper)
        .addTo(m)
    })
  })

  map.value = m
})

onUnmounted(() => {
  map.value?.remove()
})
</script>

<template>
  <div class="relative w-full h-full min-h-[550px] rounded-xl overflow-hidden shadow-2xl border border-neutral-800 bg-neutral-950">
    <!-- Map Container Target -->
    <div ref="mapContainer" class="w-full h-full min-h-[550px]" />

    <!-- Draw & Area Selection Toolbar -->
    <div class="absolute top-4 left-14 z-10 flex items-center gap-2">
      <button
        type="button"
        class="bg-neutral-900/90 hover:bg-neutral-800 text-neutral-200 hover:text-white px-3 py-1.5 rounded-lg border border-neutral-700/80 shadow-lg flex items-center gap-1.5 text-xs font-medium cursor-pointer transition backdrop-blur-md"
        @click="startDrawPolygon"
      >
        <svg class="w-3.5 h-3.5 text-orange-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
        <span>Draw Area</span>
      </button>

      <button
        v-if="activeRoiArea !== null"
        type="button"
        class="bg-neutral-900/90 hover:bg-red-950/80 text-neutral-300 hover:text-red-300 px-2.5 py-1.5 rounded-lg border border-neutral-700/80 shadow-lg text-xs font-medium cursor-pointer transition backdrop-blur-md"
        @click="clearRoi"
      >
        Clear
      </button>
    </div>

    <!-- Map UI Overlay: Satellite Provider Badge & Sensor Filters -->
    <div class="absolute top-4 right-14 z-10 flex flex-col gap-2">
      <!-- Satellite Attribution Badge -->
      <div class="bg-neutral-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-neutral-700/80 shadow-lg flex items-center gap-2 text-xs">
        <span class="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
        <span class="text-neutral-200 font-semibold">Esri World Imagery</span>
        <span class="text-[10px] text-neutral-400 font-mono">High-Res</span>
      </div>

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
            @click="filterByInstrument('ALL')"
          >
            All ({{ allHotspots.length }})
          </button>
          <button
            type="button"
            :class="[
              'px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer flex items-center gap-1',
              selectedInstrument === 'MODIS'
                ? 'bg-red-600 text-white'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
            ]"
            @click="filterByInstrument('MODIS')"
          >
            <span class="w-2 h-2 rounded-full bg-red-400 inline-block" />
            MODIS
          </button>
          <button
            type="button"
            :class="[
              'px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer flex items-center gap-1',
              selectedInstrument === 'VIIRS'
                ? 'bg-amber-600 text-white'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
            ]"
            @click="filterByInstrument('VIIRS')"
          >
            <span class="w-2 h-2 rounded-full bg-amber-400 inline-block" />
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
          <p class="font-bold text-orange-400">Area of Interest Defined</p>
          <span
            v-if="hasConsulted"
            class="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700 text-[10px] font-mono animate-pulse"
          >
            ✓ Printed to Console!
          </span>
        </div>
        <p class="text-[11px] text-neutral-400 mt-0.5">
          Area: <span class="font-mono text-white font-semibold">{{ activeRoiArea.toLocaleString() }} km²</span> |
          Hotspots: <span class="font-mono text-white font-semibold">{{ filteredCount.toLocaleString() }}</span>
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          class="px-3 py-1.5 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white font-semibold rounded-lg text-xs shadow-lg shadow-orange-600/30 transition cursor-pointer flex items-center gap-1.5"
          @click="consultRoi"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <span>Consult Area</span>
        </button>

        <button
          type="button"
          class="px-2.5 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-lg text-xs transition cursor-pointer border border-neutral-700"
          @click="clearRoi"
        >
          Clear
        </button>
      </div>
    </div>

    <!-- Map Legend -->
    <div class="absolute bottom-4 right-4 z-10 bg-neutral-900/90 backdrop-blur-md px-3 py-2 rounded-lg border border-neutral-700/80 shadow-lg text-[11px] space-y-1.5 text-neutral-300 pointer-events-none">
      <div class="font-semibold text-neutral-200">Active Hotspots (All Data)</div>
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-full bg-[#ef233c] border border-white shadow-[0_0_6px_#ff1a1a]" />
        <span>MODIS (~1 km)</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-full bg-[#ffd166] border border-white shadow-[0_0_6px_#ff9900]" />
        <span>VIIRS (375m)</span>
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
