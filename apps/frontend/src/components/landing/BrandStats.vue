<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, shallowRef } from 'vue'
import { ArrowUpRight } from '@lucide/vue'
import { z } from 'zod'
import { useApiFetch } from '@/api/useApiFetch'
import { ChartResponseSchema } from '@/api/modules/shared/schemas'
import type { AnnualMetric, AnnualRow } from '@/components/common/AnnualActivityChart.vue'

// ECharts solo se descarga cuando esta sección se monta, no con el resto de la landing.
const AnnualActivityChart = defineAsyncComponent(
  () => import('@/components/common/AnnualActivityChart.vue'),
)

const ResponseSchema = ChartResponseSchema(
  z.object({
    rows: z.array(
      z.object({
        year: z.number().int(),
        months_in_archive: z.number().int(),
        complete: z.boolean(),
        provisional_months: z.number().int().default(0),
        total_hotspots: z.number().int().nonnegative(),
        modis_count: z.number().int().nonnegative(),
        viirs_count: z.number().int().nonnegative(),
        harmonized_index: z.number(),
      }),
    ),
  }),
)

const metric = shallowRef<AnnualMetric>('raw')
const rows = shallowRef<AnnualRow[]>([])
const state = shallowRef<'loading' | 'ready' | 'error'>('loading')

async function load() {
  state.value = 'loading'
  const { data, error } = await useApiFetch('/charts/temporal/annual-stats?include_distributions=false')
    .get()
    .json<unknown>()
  const parsed = ResponseSchema.safeParse(data.value)
  if (error.value || !parsed.success) {
    state.value = 'error'
    return
  }
  // Solo años completos del archivo armonizado: sin el año parcial inicial ni datos casi en
  // tiempo real, que todavía no están armonizados.
  rows.value = parsed.data.data.rows.filter((row) => row.complete && row.provisional_months === 0)
  state.value = rows.value.length > 0 ? 'ready' : 'error'
}

onMounted(load)

const ratioFormat = new Intl.NumberFormat('es-NI', { maximumFractionDigits: 1 })

/** Cuánto crece la serie al entrar VIIRS (2011 contra 2013), cruda y armonizada. */
const jump = computed(() => {
  const before = rows.value.find((row) => row.year === 2011)
  const after = rows.value.find((row) => row.year === 2013)
  if (!before || !after || before.total_hotspots === 0 || before.harmonized_index === 0) {
    return null
  }
  return {
    raw: ratioFormat.format(after.total_hotspots / before.total_hotspots),
    harmonized: ratioFormat.format(after.harmonized_index / before.harmonized_index),
  }
})

const description = computed(() => {
  const first = rows.value[0]?.year
  const last = rows.value.at(-1)?.year
  const what = metric.value === 'raw' ? 'detecciones crudas por sensor' : 'índice armonizado'
  return `Gráfico de barras: ${what} por año en Centroamérica, de ${first} a ${last}.`
})
</script>

<template>
  <section
    id="estadisticas"
    class="landing-section landing-stats"
    aria-labelledby="stats-title"
  >
    <div class="landing-wrap">
      <div class="landing-section-heading">
        <h2 id="stats-title">Lo que cambia<br />al armonizar.</h2>
        <p v-if="jump">
          Entre 2011 y 2013 las detecciones crudas se multiplican por {{ jump.raw }}, sobre todo
          porque VIIRS empezó a observar. Con el índice armonizado el salto es de
          {{ jump.harmonized }}.
        </p>
        <p v-else>
          Sin armonizar, los años con VIIRS parecen tener mucho más fuego. El índice armonizado
          permite comparar toda la serie.
        </p>
      </div>

      <div class="landing-stats-frame">
        <div class="landing-stats-head">
          <div>
            <h3>Actividad por año</h3>
            <span class="landing-calendar-scope">Centroamérica, años completos del archivo</span>
          </div>
          <div class="landing-sensor-switch" role="group" aria-label="Métrica del gráfico">
            <button type="button" :aria-pressed="metric === 'raw'" @click="metric = 'raw'">
              Detecciones crudas
            </button>
            <button
              type="button"
              :aria-pressed="metric === 'harmonized'"
              @click="metric = 'harmonized'"
            >
              Índice armonizado
            </button>
          </div>
        </div>

        <p v-if="state === 'loading'" class="landing-calendar-state" role="status">
          Cargando las estadísticas anuales…
        </p>
        <div v-else-if="state === 'error'" class="landing-calendar-state" role="alert">
          <p>No pudimos cargar las estadísticas. Inténtalo de nuevo o abre el explorador.</p>
          <button type="button" class="landing-text-link" @click="load">Reintentar</button>
        </div>
        <AnnualActivityChart
          v-else
          :rows="rows"
          :metric="metric"
          :description="description"
          lang="es"
        />

        <p v-if="state === 'ready'" class="landing-stats-note">
          {{
            metric === 'raw'
              ? 'Gris: MODIS. Naranja: VIIRS. La línea punteada es la mediana de los años.'
              : 'Detecciones equivalentes VIIRS. La línea punteada es la mediana de los años.'
          }}
        </p>
      </div>

      <div class="landing-harmonization-line">
        <p>
          <strong>En el explorador hay más:</strong> compara cada mes con su rango histórico,
          filtra por país o dibuja tu propia área en el mapa.
        </p>
        <RouterLink :to="{ name: 'dashboard' }" class="landing-text-link"
          >Abrir estadísticas <ArrowUpRight :size="17" aria-hidden="true"
        /></RouterLink>
      </div>
    </div>
  </section>
</template>
