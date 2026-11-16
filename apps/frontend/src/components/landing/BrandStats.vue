<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, shallowRef } from 'vue'
import { ArrowUpRight } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useTemporalChartsApi } from '@/api'
import type { AnnualMetric, AnnualRow } from '@/components/common/AnnualActivityChart.vue'
import { useLocaleFormatters } from '@/i18n'

// ECharts is only downloaded when this section mounts, keeping initial landing bundle light.
const AnnualActivityChart = defineAsyncComponent(
  () => import('@/components/common/AnnualActivityChart.vue'),
)

const { t } = useI18n()
const { locale, formatDecimal } = useLocaleFormatters()
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

/** How much the series jumps when VIIRS enters (2011 vs 2013), raw and harmonized. */
const jump = computed(() => {
  const before = rows.value.find((row) => row.year === 2011)
  const after = rows.value.find((row) => row.year === 2013)
  if (!before || !after || before.total_hotspots === 0 || before.harmonized_index === 0) {
    return null
  }
  return {
    raw: formatDecimal(after.total_hotspots / before.total_hotspots),
    harmonized: formatDecimal(after.harmonized_index / before.harmonized_index),
  }
})

const description = computed(() => {
  const first = rows.value[0]?.year
  const last = rows.value.at(-1)?.year
  const what =
    metric.value === 'raw' ? t('landing.stats.whatRaw') : t('landing.stats.whatHarmonized')
  return t('landing.stats.chartDesc', { what, first, last })
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
        <h2 id="stats-title">
          {{ t('landing.stats.titleLine1') }}<br />{{ t('landing.stats.titleLine2') }}
        </h2>
        <p v-if="jump">
          {{ t('landing.stats.jumpText', { raw: jump.raw, harmonized: jump.harmonized }) }}
        </p>
        <p v-else>
          {{ t('landing.stats.fallbackText') }}
        </p>
      </div>

      <div class="landing-stats-frame">
        <div class="landing-stats-head">
          <div>
            <h3>{{ t('landing.stats.annualActivity') }}</h3>
            <span class="landing-calendar-scope">{{ t('landing.stats.scope') }}</span>
          </div>
          <div
            class="landing-sensor-switch"
            role="group"
            :aria-label="t('landing.stats.metricGroupAria')"
          >
            <button type="button" :aria-pressed="metric === 'raw'" @click="metric = 'raw'">
              {{ t('landing.stats.rawDetections') }}
            </button>
            <button
              type="button"
              :aria-pressed="metric === 'harmonized'"
              @click="metric = 'harmonized'"
            >
              {{ t('landing.stats.harmonizedIndex') }}
            </button>
          </div>
        </div>

        <p v-if="state === 'loading'" class="landing-calendar-state" role="status">
          {{ t('landing.stats.loading') }}
        </p>
        <div v-else-if="state === 'error'" class="landing-calendar-state" role="alert">
          <p>{{ t('landing.stats.error') }}</p>
          <button type="button" class="landing-text-link" @click="load">
            {{ t('common.retry') }}
          </button>
        </div>
        <AnnualActivityChart
          v-else
          :rows="rows"
          :metric="metric"
          :description="description"
          :lang="locale"
        />

        <p v-if="state === 'ready'" class="landing-stats-note">
          {{
            metric === 'raw'
              ? t('landing.stats.noteRaw')
              : t('landing.stats.noteHarmonized')
          }}
        </p>
      </div>

      <div class="landing-harmonization-line">
        <p>
          <strong>{{ t('landing.stats.morePrefix') }}</strong>
          {{ t('landing.stats.moreText') }}
        </p>
        <RouterLink :to="{ name: 'dashboard' }" class="landing-text-link"
          >{{ t('landing.stats.openStats') }} <ArrowUpRight :size="17" aria-hidden="true"
        /></RouterLink>
      </div>
    </div>
  </section>
</template>
