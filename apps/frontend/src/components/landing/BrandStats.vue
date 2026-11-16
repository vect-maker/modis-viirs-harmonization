<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, shallowRef } from 'vue'
import { ArrowUpRight } from '@lucide/vue'
import { useTemporalChartsApi } from '@/api'
import type { AnnualMetric, AnnualRow } from '@/components/common/AnnualActivityChart.vue'

// ECharts is only downloaded when this section mounts, keeping initial landing bundle light.
const AnnualActivityChart = defineAsyncComponent(
  () => import('@/components/common/AnnualActivityChart.vue'),
)

const { getAnnualStats } = useTemporalChartsApi()

const metric = shallowRef<AnnualMetric>('raw')
const rows = shallowRef<AnnualRow[]>([])
const state = shallowRef<'loading' | 'ready' | 'error'>('loading')

async function load() {
  state.value = 'loading'
  try {
    const res = await getAnnualStats({ include_distributions: false })
    // Complete archive years only (excludes initial partial year and provisional NRT feed).
    rows.value = res.rows.filter((row) => row.complete && row.provisional_months === 0)
    state.value = rows.value.length > 0 ? 'ready' : 'error'
  } catch {
    state.value = 'error'
  }
}

onMounted(load)

const ratioFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

/** How much the series jumps when VIIRS enters (2011 vs 2013), raw and harmonized. */
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
  const what = metric.value === 'raw' ? 'raw detections by sensor' : 'harmonized index'
  return `Bar chart: ${what} per year in Central America, from ${first} to ${last}.`
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
        <h2 id="stats-title">What changes<br />when you harmonize.</h2>
        <p v-if="jump">
          Between 2011 and 2013 raw detections jump by {{ jump.raw }}×, mostly because VIIRS began
          observing. With the harmonized index, the shift is {{ jump.harmonized }}×.
        </p>
        <p v-else>
          Without harmonization, years with VIIRS appear to have far more fire. The harmonized index
          makes the entire record comparable.
        </p>
      </div>

      <div class="landing-stats-frame">
        <div class="landing-stats-head">
          <div>
            <h3>Annual activity</h3>
            <span class="landing-calendar-scope">Central America, complete archive years</span>
          </div>
          <div class="landing-sensor-switch" role="group" aria-label="Chart metric">
            <button type="button" :aria-pressed="metric === 'raw'" @click="metric = 'raw'">
              Raw detections
            </button>
            <button
              type="button"
              :aria-pressed="metric === 'harmonized'"
              @click="metric = 'harmonized'"
            >
              Harmonized index
            </button>
          </div>
        </div>

        <p v-if="state === 'loading'" class="landing-calendar-state" role="status">
          Loading annual statistics…
        </p>
        <div v-else-if="state === 'error'" class="landing-calendar-state" role="alert">
          <p>Could not load statistics. Try again or open the explorer.</p>
          <button type="button" class="landing-text-link" @click="load">Retry</button>
        </div>
        <AnnualActivityChart
          v-else
          :rows="rows"
          :metric="metric"
          :description="description"
          lang="en"
        />

        <p v-if="state === 'ready'" class="landing-stats-note">
          {{
            metric === 'raw'
              ? 'Gray: MODIS. Orange: VIIRS. The dashed line is the multi-year median.'
              : 'VIIRS-equivalent detections. The dashed line is the multi-year median.'
          }}
        </p>
      </div>

      <div class="landing-harmonization-line">
        <p>
          <strong>More in the explorer:</strong> compare each month against its historical range,
          filter by country, or draw your own area on the map.
        </p>
        <RouterLink :to="{ name: 'dashboard' }" class="landing-text-link"
          >Open statistics <ArrowUpRight :size="17" aria-hidden="true"
        /></RouterLink>
      </div>
    </div>
  </section>
</template>
