<script setup lang="ts">
import { computed, h, onMounted, onUnmounted, render, shallowRef, useTemplateRef, watch } from 'vue'
import { usePermission } from '@vueuse/core'
import { ArrowUpRight, CalendarDays, Flame, MapPin } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import * as maplibregl from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useHotspotsApi, usePlatformsApi, useTemporalChartsApi, type HotspotResponse } from '@/api'
import geography from '@/data/landing-countries.json'
import { useLocaleFormatters } from '@/i18n'
import type { CalendarSensor } from '@/types/calendar'

maplibregl.setWorkerUrl(maplibreWorkerUrl)

interface CountryEntry {
  id: string
  displayName: string
  dbName: string
  polygon: GeoJSONPolygon
  bounds: [[number, number], [number, number]]
}

const SUPPORTED_IDS = new Set(['BLZ', 'CRI', 'SLV', 'GTM', 'HND', 'NIC', 'PAN'])

function computeBounds(coords: number[][][]): [[number, number], [number, number]] {
  let minLon = Infinity
  let minLat = Infinity
  let maxLon = -Infinity
  let maxLat = -Infinity
  for (const ring of coords) {
    for (const pt of ring) {
      const lon = pt[0] ?? 0
      const lat = pt[1] ?? 0
      if (lon < minLon) minLon = lon
      if (lat < minLat) minLat = lat
      if (lon > maxLon) maxLon = lon
      if (lat > maxLat) maxLat = lat
    }
  }
  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ]
}

function pointInRing(lon: number, lat: number, ring: number[][]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i]?.[0] ?? 0
    const yi = ring[i]?.[1] ?? 0
    const xj = ring[j]?.[0] ?? 0
    const yj = ring[j]?.[1] ?? 0
    const intersect = yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi + 1e-12) + xi
    if (intersect) inside = !inside
  }
  return inside
}

const COUNTRIES: CountryEntry[] = geography.countries
  .filter((c) => SUPPORTED_IDS.has(c.id))
  .map((c) => {
    const coords = c.geometry.coordinates as number[][][]
    return {
      id: c.id,
      displayName: c.name,
      dbName: c.name.replace(/ /g, '_'),
      polygon: { type: 'Polygon', coordinates: coords } as GeoJSONPolygon,
      bounds: computeBounds(coords),
    }
  })

const DEFAULT_COUNTRY = COUNTRIES.find((c) => c.id === 'NIC') ?? COUNTRIES[0]!

const { getAvailableDates, getHotspots } = useHotspotsApi()
const { getPlatforms } = usePlatformsApi()
const { getFireCalendar } = useTemporalChartsApi()
const geoPermission = usePermission('geolocation')

const platformInstruments = shallowRef<Map<string, string>>(new Map())

const { t } = useI18n()
const { formatInt, formatDecimal } = useLocaleFormatters()
const activeCountryId = shallowRef<string>(DEFAULT_COUNTRY.id)
const usedGps = shallowRef(false)
const sensor = shallowRef<CalendarSensor>('ALL')
const sensors = computed<{ value: CalendarSensor; label: string }[]>(() => [
  { value: 'ALL', label: t('common.bothSensors') },
  { value: 'MODIS', label: t('common.modis') },
  { value: 'VIIRS', label: t('common.viirs') },
])

const activeCountry = computed(
  () => COUNTRIES.find((c) => c.id === activeCountryId.value) ?? DEFAULT_COUNTRY,
)

const activeYear = shallowRef<number>(2025)
const windowLabel = shallowRef<string>('2025')
const summaryTotal = shallowRef<number | null>(null)
const summaryFrpAvg = shallowRef<number | null>(null)
const summaryDayPct = shallowRef<number | null>(null)
const mapHotspots = shallowRef<HotspotResponse[]>([])
const isLoading = shallowRef(true)

const mapContainer = useTemplateRef<HTMLDivElement>('mapContainer')
const mapInstance = shallowRef<maplibregl.Map | null>(null)
const mapReady = shallowRef(false)

function hotspotSensor(h: HotspotResponse): 'MODIS' | 'VIIRS' {
  const inst = (platformInstruments.value.get(h.platform_id) ?? '').toUpperCase()
  return inst.includes('MODIS') ? 'MODIS' : 'VIIRS'
}

const visibleHotspots = computed(() =>
  mapHotspots.value.filter((h) => sensor.value === 'ALL' || hotspotSensor(h) === sensor.value),
)

function buildHotspotsGeoJson(): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: 'FeatureCollection',
    features: visibleHotspots.value.map((h) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [h.longitude, h.latitude] },
      properties: {
        sensor: hotspotSensor(h),
      },
    })),
  }
}

function syncMapCountryAndData() {
  const m = mapInstance.value
  if (!m || !mapReady.value) return

  const countrySrc = m.getSource('landing-country') as maplibregl.GeoJSONSource | undefined
  if (countrySrc) {
    countrySrc.setData({
      type: 'Feature',
      geometry: activeCountry.value.polygon as GeoJSON.Polygon,
      properties: {},
    })
  }

  const ptsSrc = m.getSource('landing-hotspots') as maplibregl.GeoJSONSource | undefined
  if (ptsSrc) {
    ptsSrc.setData(buildHotspotsGeoJson())
  }

  m.fitBounds(activeCountry.value.bounds, { padding: 26, duration: 0 })
}

async function loadCountrySummary() {
  isLoading.value = true
  try {
    const dates = await getAvailableDates()
    const maxDate = dates.max_date ?? '2025-05-15'
    const yr = Number(maxDate.slice(0, 4)) || 2025
    // Prefer the latest complete archive year (<= 2025) for annual summary if maxDate is 2026 NRT
    const summaryYr = yr >= 2026 ? 2025 : yr
    activeYear.value = summaryYr
    windowLabel.value = String(summaryYr)

    const endMs = Date.parse(`${maxDate}T00:00:00Z`)
    const startDate = Number.isNaN(endMs)
      ? `${summaryYr}-04-01`
      : new Date(endMs - 30 * 86_400_000).toISOString().slice(0, 10)

    const [calRes, hsRes, platsRes] = await Promise.allSettled([
      getFireCalendar({
        year: summaryYr,
        country: activeCountry.value.dbName,
        instrument: sensor.value === 'ALL' ? undefined : sensor.value,
        aggregation: 'month',
      }),
      getHotspots({
        start_date: startDate,
        end_date: maxDate,
        polygon: activeCountry.value.polygon,
        limit: 100,
      }),
      platformInstruments.value.size === 0 ? getPlatforms({ limit: 50 }) : Promise.resolve(null),
    ])

    if (platsRes.status === 'fulfilled' && platsRes.value) {
      platformInstruments.value = new Map(platsRes.value.data.map((p) => [p.id, p.instrument]))
    }

    if (calRes.status === 'fulfilled') {
      const cal = calRes.value
      summaryTotal.value = cal.total_hotspots
      summaryFrpAvg.value = cal.frp_average
      summaryDayPct.value =
        cal.total_hotspots > 0
          ? Math.round((cal.daytime_hotspots / cal.total_hotspots) * 100)
          : null
    }

    if (hsRes.status === 'fulfilled') {
      mapHotspots.value = hsRes.value.data
    }
    syncMapCountryAndData()
  } catch {
    // Keep last known values if backend is unreachable
  } finally {
    isLoading.value = false
  }
}

function detectCountryFromGps() {
  if (typeof navigator === 'undefined' || !('geolocation' in navigator)) return
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lon = pos.coords.longitude
      const lat = pos.coords.latitude
      const matched = COUNTRIES.find((c) => {
        const outerRing = c.polygon.coordinates[0]
        return outerRing ? pointInRing(lon, lat, outerRing) : false
      })
      if (matched && matched.id !== activeCountryId.value) {
        activeCountryId.value = matched.id
        usedGps.value = true
      }
    },
    () => {
      // Permission denied or unavailable -> keep Nicaragua default
    },
    { enableHighAccuracy: false, timeout: 5000, maximumAge: 300_000 },
  )
}

watch(
  geoPermission,
  (state) => {
    if (state === 'granted') detectCountryFromGps()
  },
  { immediate: true },
)

watch([activeCountryId, sensor], () => {
  void loadCountrySummary()
})

watch(visibleHotspots, () => {
  const m = mapInstance.value
  if (!m || !mapReady.value) return
  const ptsSrc = m.getSource('landing-hotspots') as maplibregl.GeoJSONSource | undefined
  if (ptsSrc) ptsSrc.setData(buildHotspotsGeoJson())
})

onMounted(() => {
  if (mapContainer.value) {
    const m = new maplibregl.Map({
      container: mapContainer.value,
      interactive: false,
      attributionControl: false,
      style: {
        version: 8,
        sources: {
          'esri-imagery-src': {
            type: 'raster',
            tiles: [
              'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}?blankTile=false',
            ],
            tileSize: 256,
            maxzoom: 12,
          },
        },
        layers: [
          {
            id: 'esri-imagery',
            type: 'raster',
            source: 'esri-imagery-src',
            paint: {
              'raster-brightness-max': 0.55,
              'raster-saturation': -0.35,
              'raster-contrast': 0.1,
            },
          },
        ],
      },
      bounds: activeCountry.value.bounds,
      fitBoundsOptions: { padding: 26 },
    })

    m.on('load', () => {
      m.addSource('landing-country', {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: activeCountry.value.polygon as GeoJSON.Polygon,
          properties: {},
        },
      })
      m.addLayer({
        id: 'landing-country-fill',
        type: 'fill',
        source: 'landing-country',
        paint: {
          'fill-color': '#8FBF9F',
          'fill-opacity': 0.08,
        },
      })
      m.addLayer({
        id: 'landing-country-line',
        type: 'line',
        source: 'landing-country',
        paint: {
          'line-color': '#8FBF9F',
          'line-width': 1.5,
          'line-opacity': 0.75,
        },
      })
      m.addSource('landing-hotspots', {
        type: 'geojson',
        data: buildHotspotsGeoJson(),
      })
      m.addLayer({
        id: 'landing-hotspots-glow',
        type: 'circle',
        source: 'landing-hotspots',
        paint: {
          'circle-radius': 10,
          'circle-color': ['match', ['get', 'sensor'], 'MODIS', '#f59e0b', '#38bdf8'],
          'circle-opacity': 0.25,
          'circle-blur': 0.8,
        },
      })

      const flameStyles = [
        { id: 'landing-flame-modis', fill: '#f59e0b', stroke: '#fef08a' },
        { id: 'landing-flame-viirs', fill: '#0ea5e9', stroke: '#bae6fd' },
      ] as const

      let loadedIcons = 0
      const ensureSymbolLayer = () => {
        if (!mapInstance.value || m.getLayer('landing-hotspots-symbol')) return
        m.addLayer({
          id: 'landing-hotspots-symbol',
          type: 'symbol',
          source: 'landing-hotspots',
          layout: {
            'icon-image': [
              'match',
              ['get', 'sensor'],
              'MODIS',
              'landing-flame-modis',
              'landing-flame-viirs',
            ],
            'icon-size': 0.62,
            'icon-allow-overlap': true,
            'icon-anchor': 'bottom',
          },
        })
      }

      for (const style of flameStyles) {
        const svgHost = document.createElement('div')
        render(
          h(Flame, {
            size: 36,
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

        const img = new Image(36, 36)
        img.onload = () => {
          if (!mapInstance.value) return
          if (!m.hasImage(style.id)) {
            m.addImage(style.id, img, { pixelRatio: 2 })
          }
          loadedIcons += 1
          if (loadedIcons === flameStyles.length) {
            ensureSymbolLayer()
          }
        }
        img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgMarkup)}`
      }

      mapReady.value = true
      syncMapCountryAndData()
    })

    mapInstance.value = m
  }

  void loadCountrySummary()
})

onUnmounted(() => {
  mapInstance.value?.remove()
  mapInstance.value = null
})
</script>

<template>
  <div class="landing-map-frame">
    <div class="landing-map-toolbar">
      <div class="landing-map-title">
        <img src="/favicon.svg" alt="" width="27" height="27" /><span>{{
          t('landing.mapPreview.title')
        }}</span>
      </div>
      <RouterLink
        :to="{ name: 'dashboard' }"
        class="landing-icon-link"
        :aria-label="t('landing.mapPreview.openFullMap')"
        ><ArrowUpRight :size="19" aria-hidden="true"
      /></RouterLink>
    </div>
    <div class="landing-map-filters">
      <span>
        <MapPin :size="14" aria-hidden="true" />
        {{
          usedGps
            ? t('landing.mapPreview.gpsTag', { country: activeCountry.displayName })
            : activeCountry.displayName
        }}
      </span>
      <span><CalendarDays :size="14" aria-hidden="true" /> {{ windowLabel }}</span>
      <span class="landing-preview-label">{{ t('landing.mapPreview.live') }}</span>
    </div>
    <div class="landing-map-canvas">
      <div
        ref="mapContainer"
        class="h-full w-full"
        role="img"
        :aria-label="t('landing.mapPreview.mapAria', { country: activeCountry.displayName })"
      />
      <div
        class="landing-map-readout z-10 rounded-lg border border-white/10 bg-[#0b1215]/75 px-3 py-2 backdrop-blur-sm"
        role="status"
        aria-live="polite"
      >
        <span class="landing-map-readout-label">{{
          t('landing.mapPreview.detectionsIn', { year: activeYear })
        }}</span>
        <strong>{{ summaryTotal !== null ? formatInt(summaryTotal) : '—' }}</strong>
        <span>
          <i class="landing-status-dot" />
          {{ sensor === 'ALL' ? 'MODIS + VIIRS' : sensor }}
          <template v-if="summaryFrpAvg !== null">
            · {{ t('landing.mapPreview.mwAvg', { value: formatDecimal(summaryFrpAvg) }) }}
          </template>
          <template v-if="summaryDayPct !== null">
            · {{ t('landing.mapPreview.dayPct', { value: summaryDayPct }) }}
          </template>
        </span>
      </div>
      <div class="landing-map-key z-10 rounded-md bg-[#0b1215]/75 px-2.5 py-1 backdrop-blur-sm">
        <span class="inline-flex items-center gap-1"
          ><Flame :size="12" class="text-amber-300 fill-amber-500" aria-hidden="true" />
          {{ t('common.modis') }}</span
        >
        <span class="inline-flex items-center gap-1"
          ><Flame :size="12" class="text-sky-200 fill-sky-500" aria-hidden="true" />
          {{ t('common.viirs') }}</span
        >
      </div>
    </div>
    <div
      class="landing-sensor-switch"
      role="group"
      :aria-label="t('landing.mapPreview.sensorFilterAria')"
    >
      <button
        v-for="option in sensors"
        :key="option.value"
        type="button"
        :aria-pressed="sensor === option.value"
        @click="sensor = option.value"
      >
        {{ option.label }}
      </button>
    </div>
    <div class="landing-map-source">
      <span>{{ t('landing.mapPreview.sourceFooter') }}</span>
      <span>{{
        isLoading
          ? t('common.loading')
          : t('landing.mapPreview.recentDetections', { count: formatInt(visibleHotspots.length) })
      }}</span>
    </div>
  </div>
</template>
