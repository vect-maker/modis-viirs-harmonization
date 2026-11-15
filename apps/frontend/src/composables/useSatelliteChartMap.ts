import { onMounted, onUnmounted, shallowRef, type ShallowRef } from 'vue'
import { useResizeObserver } from '@vueuse/core'
import * as maplibregl from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'

maplibregl.setWorkerUrl(maplibreWorkerUrl)

export const CENTRAL_AMERICA_BOUNDS: [[number, number], [number, number]] = [
  [-92.3, 7.2],
  [-77.1, 18.5],
]

const ESRI_WORLD_IMAGERY_TILES =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}?blankTile=false'

export interface UseSatelliteChartMapOptions {
  container: Readonly<ShallowRef<HTMLElement | null>>
  onLoad?: (map: maplibregl.Map) => void
}

/**
 * Mounts a 2D MapLibre GL map with the Esri World Imagery satellite basemap
 * for geospatial diagnostic charts, handling resize and bounds fitting.
 */
export function useSatelliteChartMap(options: UseSatelliteChartMapOptions) {
  const map = shallowRef<maplibregl.Map | null>(null)
  const isLoaded = shallowRef(false)
  let lastBounds: [[number, number], [number, number]] = CENTRAL_AMERICA_BOUNDS

  useResizeObserver(options.container, () => {
    map.value?.resize()
  })

  function computeBounds(coords: Iterable<[number, number]>): [[number, number], [number, number]] {
    let minLon = Infinity
    let minLat = Infinity
    let maxLon = -Infinity
    let maxLat = -Infinity
    let count = 0

    for (const [lon, lat] of coords) {
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue
      if (lon < minLon) minLon = lon
      if (lon > maxLon) maxLon = lon
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
      count += 1
    }

    if (count === 0) return CENTRAL_AMERICA_BOUNDS

    // Pad tiny or single-point spans so fitBounds does not zoom in excessively.
    if (maxLon - minLon < 0.05) {
      minLon -= 0.25
      maxLon += 0.25
    }
    if (maxLat - minLat < 0.05) {
      minLat -= 0.25
      maxLat += 0.25
    }

    return [
      [minLon, minLat],
      [maxLon, maxLat],
    ]
  }

  function fitToCoordinates(coords: Iterable<[number, number]>, duration = 200) {
    lastBounds = computeBounds(coords)
    if (!map.value || !isLoaded.value) return
    map.value.fitBounds(lastBounds, { padding: 32, maxZoom: 11, duration })
  }

  function resetView() {
    if (!map.value) return
    map.value.fitBounds(lastBounds, { padding: 32, maxZoom: 11, duration: 250 })
  }

  onMounted(() => {
    if (!options.container.value) return

    const instance = new maplibregl.Map({
      container: options.container.value,
      style: {
        version: 8,
        projection: { type: 'mercator' },
        sources: {
          'esri-imagery-src': {
            type: 'raster',
            tiles: [ESRI_WORLD_IMAGERY_TILES],
            tileSize: 256,
            attribution: 'Esri, Maxar, Earthstar Geographics',
            maxzoom: 17,
          },
        },
        layers: [
          {
            id: 'background',
            type: 'background',
            paint: { 'background-color': '#0d1117' },
          },
          {
            id: 'esri-imagery',
            type: 'raster',
            source: 'esri-imagery-src',
            paint: {
              'raster-brightness-max': 0.82,
              'raster-contrast': 0.08,
              'raster-saturation': -0.1,
            },
          },
        ],
      },
      bounds: CENTRAL_AMERICA_BOUNDS,
      fitBoundsOptions: { padding: 24 },
      minZoom: 2,
      maxZoom: 17,
      dragRotate: false,
      pitchWithRotate: false,
      attributionControl: false,
    })

    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left')
    instance.addControl(new maplibregl.ScaleControl({ maxWidth: 90, unit: 'metric' }), 'bottom-left')

    instance.on('load', () => {
      isLoaded.value = true
      options.onLoad?.(instance)
    })

    map.value = instance
  })

  onUnmounted(() => {
    isLoaded.value = false
    map.value?.remove()
    map.value = null
  })

  return {
    map,
    isLoaded,
    fitToCoordinates,
    resetView,
  }
}
