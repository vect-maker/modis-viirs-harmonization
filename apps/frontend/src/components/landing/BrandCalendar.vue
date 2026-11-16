<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { ArrowUpRight, ChevronLeft, ChevronRight, Info } from '@lucide/vue'
import { useCalendarStore } from '@/stores/calendar'
import type { CalendarCell, CalendarSensor } from '@/types/calendar'
import { calendarCount } from '@/utils/historicalCalendar'
import { getThermalPalette } from '@/utils/themeColors'

const BurningCalendar = defineAsyncComponent(
  () => import('@/components/common/BurningCalendar.vue'),
)

const calendarStore = useCalendarStore()
const { archive, isLoading, hasLoaded, error } = storeToRefs(calendarStore)
onMounted(() => {
  void calendarStore.fetchHistoricalCalendar()
})

const year = shallowRef(2024)
const month = shallowRef(5)
const sensor = shallowRef<CalendarSensor>('ALL')
const format = new Intl.NumberFormat('es-NI')
const labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
const fullLabels = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
]
const firstYear = computed(() =>
  archive.value.firstDetection ? Number(archive.value.firstDetection.slice(0, 4)) : 2020,
)
// Último año con los 12 meses en el archivo: deja fuera el año en curso, que llega
// incompleto y desde el feed casi en tiempo real.
const lastYear = computed(() => {
  const monthsPerYear = new Map<number, number>()
  for (const item of archive.value.months) {
    monthsPerYear.set(item.year, (monthsPerYear.get(item.year) ?? 0) + 1)
  }
  const complete = [...monthsPerYear].filter(([, n]) => n === 12).map(([y]) => y)
  return complete.length > 0 ? Math.max(...complete) : 2025
})
const isReady = computed(() => hasLoaded.value && archive.value.months.length > 0)
const years = computed(() =>
  Array.from({ length: lastYear.value - firstYear.value + 1 }, (_, i) => lastYear.value - i),
)
const recentYears = computed(() =>
  Array.from({ length: 6 }, (_, i) => lastYear.value - 5 + i),
)
const index = computed(
  () => new Map(archive.value.months.map((item) => [`${item.year}-${item.month}`, item])),
)
const maximum = computed(() =>
  Math.max(
    1,
    ...archive.value.months
      .filter((item) => item.year <= lastYear.value)
      .map((item) => calendarCount(item, sensor.value) ?? 0),
  ),
)
const rows = computed(() =>
  recentYears.value.map((y) => ({
    year: y,
    cells: labels.map((_, i): CalendarCell => {
      const m = i + 1
      const item = index.value.get(`${y}-${m}`)
      return {
        year: y,
        month: m,
        count: calendarCount(item, sensor.value),
      }
    }),
  })),
)
const palette = computed(() => getThermalPalette())
function onSelectPeriod(selectedYear: number, selectedMonth: number) {
  year.value = selectedYear
  month.value = selectedMonth
}
const selected = computed(() => index.value.get(`${year.value}-${month.value}`))
const selectedCount = computed(() => calendarCount(selected.value, sensor.value))
const yearCells = computed(() =>
  labels.map((label, i) => ({
    label,
    month: i + 1,
    count: calendarCount(index.value.get(`${year.value}-${i + 1}`), sensor.value),
  })),
)
const peakMonth = computed(() =>
  yearCells.value.reduce(
    (best, cell) => ((cell.count ?? -1) > (best.count ?? -1) ? cell : best),
    yearCells.value[0]!,
  ),
)
</script>

<template>
  <section id="datos" class="landing-section landing-data-section" aria-labelledby="calendar-title">
    <div class="landing-wrap">
      <div class="landing-section-heading">
        <h2 id="calendar-title">El calendario<br />del fuego.</h2>
        <p>
          ¿Qué meses concentran más detecciones? Recorre el archivo desde 2000, cambia el mes y el
          sensor, y encuentra tus propias preguntas.
        </p>
      </div>
      <div class="landing-calendar-layout">
        <div class="landing-calendar-frame">
          <div class="landing-calendar-frame-head">
            <div>
              <h3>Actividad por mes</h3>
              <span class="landing-calendar-scope">Centroamérica, los 7 países</span>
            </div>
            <span class="landing-source-chip">NASA FIRMS</span>
          </div>
          <p v-if="isLoading && !isReady" class="landing-calendar-state" role="status">
            Cargando el archivo de detecciones…
          </p>
          <div v-else-if="!isReady" class="landing-calendar-state" role="alert">
            <p>No pudimos cargar el calendario. Revisa la conexión e inténtalo de nuevo.</p>
            <button
              v-if="error"
              type="button"
              class="landing-text-link"
              @click="calendarStore.fetchHistoricalCalendar()"
            >
              Reintentar
            </button>
          </div>
          <div v-else class="landing-calendar-matrix">
            <BurningCalendar
              :rows="rows"
              :max-count="maximum"
              :selected-period="{ year, month }"
              @select="onSelectPeriod"
            />
          </div>
          <div v-if="isReady" class="landing-calendar-legend">
            <span>Menos detecciones</span>
            <div aria-hidden="true">
              <i v-for="color in palette" :key="color" :style="{ backgroundColor: color }" />
            </div>
            <span>Más detecciones</span>
          </div>
          <div v-if="isReady" class="landing-calendar-controls">
            <div class="landing-year-picker">
              <button
                type="button"
                :disabled="year <= firstYear"
                aria-label="Año anterior"
                @click="year--"
              >
                <ChevronLeft :size="18" aria-hidden="true" /></button
              ><label
                ><span class="landing-sr-only">Año a consultar</span
                ><select v-model="year">
                  <option v-for="option in years" :key="option" :value="option">
                    {{ option }}
                  </option>
                </select></label
              ><button
                type="button"
                :disabled="year >= lastYear"
                aria-label="Año siguiente"
                @click="year++"
              >
                <ChevronRight :size="18" aria-hidden="true" />
              </button>
            </div>
            <label class="landing-calendar-sensor"
              ><span class="landing-sr-only">Sensor del calendario</span
              ><select v-model="sensor">
                <option value="ALL">Ambos sensores</option>
                <option value="MODIS">MODIS</option>
                <option value="VIIRS">VIIRS</option>
              </select></label
            >
          </div>
          <div
            v-if="isReady"
            class="landing-month-picker"
            role="group" :aria-label="`Mes de ${year} a consultar`">
            <button
              v-for="cell in yearCells"
              :key="cell.month"
              type="button"
              :aria-pressed="month === cell.month"
              :aria-label="`${fullLabels[cell.month - 1]} de ${year}: ${cell.count === null ? 'sin datos disponibles' : format.format(cell.count) + ' detecciones'}`"
              @click="month = cell.month"
            >
              {{ cell.label }}
            </button>
          </div>
        </div>
        <div class="landing-calendar-insight">
          <div
            v-if="isReady"
            class="landing-calendar-result"
            role="status" aria-live="polite" aria-atomic="true">
            <p class="landing-result-period">{{ fullLabels[month - 1] }} de {{ year }}</p>
            <strong>{{ selectedCount === null ? '—' : format.format(selectedCount) }}</strong>
            <p>
              {{
                selectedCount === null
                  ? 'Sin datos disponibles para este sensor y periodo.'
                  : 'detecciones satelitales registradas'
              }}
            </p>
          </div>
          <div v-if="isReady" class="landing-peak-note">
            <span>Mes con más detecciones en {{ year }}</span
            ><strong>{{
              (peakMonth.count ?? 0) > 0 ? fullLabels[peakMonth.month - 1] : 'Sin datos'
            }}</strong>
          </div>
          <div class="landing-science-note">
            <Info :size="18" aria-hidden="true" />
            <p>
              Conteos crudos de detecciones, sin armonizar. Una detección es un píxel con calor
              anómalo, no un incendio individual.
            </p>
          </div>
          <RouterLink :to="{ name: 'dashboard' }" class="landing-text-link"
            >Consultar el explorador <ArrowUpRight :size="17" aria-hidden="true"
          /></RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>
