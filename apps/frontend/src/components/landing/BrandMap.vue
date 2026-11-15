<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { ArrowUpRight, CalendarDays, MapPin } from '@lucide/vue'
import geography from '@/data/landing-countries.json'
import preview from '@/data/landing-hotspots.json'
import type { CalendarSensor } from '@/types/calendar'

const sensor = shallowRef<CalendarSensor>('ALL')
const sensors: { value: CalendarSensor; label: string }[] = [
  { value: 'ALL', label: 'Ambos sensores' },
  { value: 'MODIS', label: 'MODIS' },
  { value: 'VIIRS', label: 'VIIRS' },
]
const dots = preview.dots.map(([x = 0, y = 0, instrument = 0, count = 1], index) => ({
  x,
  y,
  instrument,
  count,
  id: index,
}))
const visibleDots = computed(() =>
  dots.filter(
    (dot) => sensor.value === 'ALL' || dot.instrument === (sensor.value === 'MODIS' ? 0 : 1),
  ),
)
const count = computed(() =>
  sensor.value === 'ALL' ? preview.total : sensor.value === 'MODIS' ? preview.modis : preview.viirs,
)
const number = new Intl.NumberFormat('es-NI')
const boundaries = geography.countries.map((country) => {
  const polygons = (
    country.geometry.type === 'Polygon'
      ? [country.geometry.coordinates]
      : country.geometry.coordinates
  ) as number[][][][]
  const path = polygons
    .map((polygon) =>
      polygon
        .map(
          (ring) =>
            ring
              .map(
                ([lon = 0, lat = 0], i) =>
                  `${i ? 'L' : 'M'}${((lon + 88.5) * 90).toFixed(2)},${((16 - lat) * 92).toFixed(2)}`,
              )
              .join(' ') + ' Z',
        )
        .join(' '),
    )
    .join(' ')
  return { id: country.id, path }
})
</script>

<template>
  <div class="landing-map-frame">
    <div class="landing-map-toolbar">
      <div class="landing-map-title">
        <img src="/favicon.svg" alt="" width="27" height="27" /><span>Explorador de actividad</span>
      </div>
      <RouterLink :to="{ name: 'dashboard' }" class="landing-icon-link" aria-label="Abrir el mapa completo"
        ><ArrowUpRight :size="19" aria-hidden="true"
      /></RouterLink>
    </div>
    <div class="landing-map-filters">
      <span><MapPin :size="14" aria-hidden="true" /> Nicaragua</span
      ><span><CalendarDays :size="14" aria-hidden="true" /> Mayo 2024</span
      ><span class="landing-preview-label">VISTA PREVIA</span>
    </div>
    <div class="landing-map-canvas">
      <svg
        viewBox="0 0 585 570"
        role="img"
        :aria-label="`Distribución de ${number.format(count)} detecciones de la muestra de Nicaragua, mayo de 2024. Puntos agrupados por cercanía.`"
      >
        <defs>
          <pattern id="preview-map-grid" width="65" height="65" patternUnits="userSpaceOnUse">
            <path d="M 65 0 L 0 0 0 65" fill="none" stroke="currentColor" stroke-width="0.5" />
          </pattern>
          <radialGradient id="preview-map-light">
            <stop offset="0" stop-color="#8FBF9F" stop-opacity="0.12" />
            <stop offset="1" stop-color="#8FBF9F" stop-opacity="0" />
          </radialGradient>
        </defs>
        <rect width="585" height="570" class="map-water" />
        <rect width="585" height="570" fill="url(#preview-map-light)" />
        <rect width="585" height="570" fill="url(#preview-map-grid)" class="map-grid" />
        <path
          v-for="country in boundaries"
          :key="country.id"
          :d="country.path"
          :class="country.id === 'NIC' ? 'map-country map-country-nicaragua' : 'map-country'"
        />
        <g class="map-place-labels" aria-hidden="true">
          <text x="156" y="85">HONDURAS</text>
          <text x="365" y="492">COSTA RICA</text>
          <text x="333" y="240" class="map-nicaragua-label">NICARAGUA</text>
          <text x="70" y="398" class="map-ocean-label" transform="rotate(-28 70 398)">
            OCÉANO PACÍFICO
          </text>
          <text x="457" y="175" class="map-ocean-label">MAR CARIBE</text>
        </g>
        <g aria-hidden="true">
          <circle
            v-for="dot in visibleDots"
            :key="dot.id"
            :cx="dot.x"
            :cy="dot.y"
            :r="1.6 + Math.min(2.1, Math.log1p(dot.count) * 0.45)"
            :class="dot.instrument === 0 ? 'map-dot map-dot-modis' : 'map-dot map-dot-viirs'"
          />
        </g>
      </svg>
      <div class="landing-map-readout" role="status" aria-live="polite">
        <span class="landing-map-readout-label">DETECCIONES EN LA MUESTRA</span
        ><strong>{{ number.format(count) }}</strong
        ><span
          ><i class="landing-status-dot" /> {{ sensor === 'ALL' ? 'MODIS + VIIRS' : sensor }}</span
        >
      </div>
      <div class="landing-map-coordinate" aria-hidden="true">14° N<br />12° N<br />10° N</div>
      <div class="landing-map-key">
        <span><i class="modis-dot" /> MODIS</span><span><i class="viirs-dot" /> VIIRS</span>
      </div>
    </div>
    <div class="landing-sensor-switch" role="group" aria-label="Sensor de la vista previa">
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
      <span>NASA FIRMS · puntos agrupados</span><span>Muestra local</span>
    </div>
  </div>
</template>
