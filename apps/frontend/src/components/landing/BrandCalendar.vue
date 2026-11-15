<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { ArrowUpRight, ChevronLeft, ChevronRight, Info } from '@lucide/vue'
import { useCalendarStore } from '@/stores/calendar'
import type { CalendarSensor } from '@/types/calendar'
import { calendarCount } from '@/utils/historicalCalendar'

const calendarStore = useCalendarStore()
const { archive } = storeToRefs(calendarStore)
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
const lastYear = computed(() =>
  archive.value.lastDetection ? Number(archive.value.lastDetection.slice(0, 4)) : 2025,
)
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
  Math.max(1, ...archive.value.months.map((item) => calendarCount(item, sensor.value) ?? 0)),
)
const rows = computed(() =>
  recentYears.value.map((y) => ({
    year: y,
    cells: labels.map((label, i) => ({
      label,
      month: i + 1,
      count: calendarCount(index.value.get(`${y}-${i + 1}`), sensor.value),
    })),
  })),
)
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
function heat(count: number | null) {
  if (count === null) return 'var(--landing-heat-empty)'
  if (count === 0) return 'var(--landing-heat-0)'
  const step = Math.min(5, Math.floor((Math.log1p(count) / Math.log1p(maximum.value)) * 6))
  return `var(--landing-heat-${step})`
}
</script>

<template>
  <section id="datos" class="landing-section landing-data-section" aria-labelledby="calendar-title">
    <div class="landing-wrap">
      <div class="landing-section-top">
        <span class="landing-section-index">02 / COMPRENDER</span
        ><span class="landing-section-note">DEL DATO A LA PREGUNTA</span>
      </div>
      <div class="landing-section-heading">
        <h2 id="calendar-title">El calendario de<br /><span>tu territorio.</span></h2>
        <p>
          ¿Qué meses concentran más detecciones? Empieza por Nicaragua, cambia el periodo y
          encuentra tus propias preguntas.
        </p>
      </div>
      <div class="landing-calendar-layout">
        <div class="landing-calendar-frame">
          <div class="landing-calendar-frame-head">
            <div>
              <span class="landing-kicker">NICARAGUA / AGREGADO NACIONAL</span>
              <h3>Actividad por mes</h3>
            </div>
            <span class="landing-source-chip">NASA FIRMS</span>
          </div>
          <div
            class="landing-calendar-matrix"
            role="img"
            aria-label="Calendario nacional de detecciones entre 2020 y 2025. El tono indica la cantidad en escala logarítmica; consulta las cifras mediante los controles inferiores."
          >
            <div class="landing-matrix-row landing-matrix-labels">
              <span>AÑO</span><span v-for="label in labels" :key="label">{{ label }}</span>
            </div>
            <div
              v-for="row in rows"
              :key="row.year"
              class="landing-matrix-row"
              :class="{ 'is-selected-year': year === row.year }"
            >
              <span class="landing-matrix-year">{{ row.year }}</span
              ><span
                v-for="cell in row.cells"
                :key="cell.month"
                class="landing-heat-cell"
                :style="{ backgroundColor: heat(cell.count) }"
                ><span class="landing-sr-only"
                  >{{ cell.label }}:
                  {{ cell.count === null ? 'sin datos' : format.format(cell.count) }}</span
                ></span
              >
            </div>
          </div>
          <div class="landing-calendar-legend">
            <span>Menos detecciones</span>
            <div aria-hidden="true">
              <i
                v-for="level in 6"
                :key="level"
                :style="{ backgroundColor: `var(--landing-heat-${level - 1})` }"
              />
            </div>
            <span>Más detecciones</span>
          </div>
          <div class="landing-calendar-controls">
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
          <div class="landing-month-picker" role="group" :aria-label="`Mes de ${year} a consultar`">
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
          <span class="landing-kicker">UNA MIRADA A LOS DATOS</span>
          <div class="landing-calendar-result" role="status" aria-live="polite" aria-atomic="true">
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
          <div class="landing-peak-note">
            <span>MES CON MÁS DETECCIONES EN {{ year }}</span
            ><strong>{{
              (peakMonth.count ?? 0) > 0 ? fullLabels[peakMonth.month - 1] : 'Sin datos'
            }}</strong>
          </div>
          <div class="landing-science-note">
            <Info :size="18" aria-hidden="true" />
            <p>
              Estos son conteos originales, aún sin armonizar y con cobertura por verificar. Una
              detección no equivale a un incendio individual.
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
