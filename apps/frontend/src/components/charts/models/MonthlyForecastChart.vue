<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { useModelChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useChartFiltersStore } from '@/stores/chartFilters'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import MonthlyForecastRenderer from '@/components/common/MonthlyForecastChart.vue'

const filtersStore = useChartFiltersStore()
const { metric, activePolygon } = storeToRefs(filtersStore)
const { getMonthlyForecast } = useModelChartsApi()

const HORIZON_OPTIONS = [
  { value: '3', label: '3 months' },
  { value: '6', label: '6 months' },
  { value: '12', label: '12 months' },
] as const

const RANGE_OPTIONS = [
  { value: '2012-2025', label: '2012 – 2025 (VIIRS baseline)' },
  { value: '2001-2025', label: '2001 – 2025 (Full archive)' },
  { value: '2012-2026', label: '2012 – 2026 (inc. NRT)' },
] as const

const futureMonths = shallowRef<'3' | '6' | '12'>('6')
const trainingRange = shallowRef<string>('2012-2025')

const {
  data: result,
  isLoading,
  error,
  refresh,
} = useChartLifecycle({
  fetcher: () => {
    const [startStr, endStr] = trainingRange.value.split('-')
    return getMonthlyForecast({
      train_ratio: 0.8,
      future_months: futureMonths.value,
      start_year: startStr ?? '2012',
      end_year: endStr ?? '2025',
      metric: metric.value,
      polygon: activePolygon.value,
    })
  },
  watchSources: [futureMonths, trainingRange, activePolygon, metric],
})

const intFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const decFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })
const includesNrt = computed(() => trainingRange.value.endsWith('2026'))

const summaryText = computed(() => {
  if (!result.value) return ''
  const m = result.value.metrics
  const next = result.value.future[0]
  const nextStr = next
    ? ` Next month (${next.month}) projects ${intFmt.format(Math.round(next.predicted))} detections (80% CI ${intFmt.format(Math.round(next.lower_80))}–${intFmt.format(Math.round(next.upper_80))}).`
    : ''
  return `Trained on ${m.train_months} months and validated on ${m.test_months} holdout months (R² = ${m.r2.toFixed(2)}, sMAPE = ${decFmt.format(m.smape_pct)}%).${nextStr}`
})

const chartDescription = computed(
  () => `Monthly seasonal forecast chart with confidence intervals. ${summaryText.value}`,
)
</script>

<template>
  <section aria-labelledby="monthly-forecast-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="monthly-forecast-title" class="text-base font-semibold text-ink-primary">
            Seasonal monthly forecast (Autoregressive Ridge)
          </h2>
          <span
            class="rounded-md border border-border-subtle bg-white/[0.04] px-2 py-0.5 text-[11px] font-medium text-ink-secondary"
          >
            {{ activePolygon ? 'Drawn area (Polygon)' : 'All regions' }} ·
            {{ metric === 'harmonized' ? 'Harmonized index' : 'Raw monthly counts' }}
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Fits a Ridge regression with 1-, 2-, and 12-month lags plus seasonal Fourier harmonics,
          reporting holdout validation errors and 80% / 95% confidence bands.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup
          v-model="futureMonths"
          :options="HORIZON_OPTIONS"
          label="Forecast horizon"
        />
        <BaseSelect
          v-model="trainingRange"
          :options="RANGE_OPTIONS"
          label="Training period"
          :disabled="isLoading && result === null"
        />
      </div>
    </header>

    <div class="space-y-4 p-5">
      <div
        v-if="error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-100"
      >
        <span>Could not load seasonal forecast. {{ error }}</span>
        <button
          type="button"
          class="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-red-300/40 px-3 text-xs font-medium hover:bg-red-400/10 focus-visible:outline-2 focus-visible:outline-focus"
          @click="refresh"
        >
          <RotateCw aria-hidden="true" class="h-3.5 w-3.5" />
          Try again
        </button>
      </div>

      <div
        v-if="result === null && isLoading"
        class="h-[22rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
      />

      <template v-else-if="result !== null">
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
            <p class="text-[11px] text-ink-muted">Validation R²</p>
            <p
              class="mt-1 font-mono text-lg font-semibold tabular-nums"
              :class="result.metrics.r2 >= 0.5 ? 'text-accent-bright' : 'text-ink-primary'"
            >
              {{ result.metrics.r2.toFixed(3) }}
            </p>
          </div>
          <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
            <p class="text-[11px] text-ink-muted">MAE / RMSE</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums text-ink-primary">
              {{ intFmt.format(Math.round(result.metrics.mae)) }}
              <span class="text-xs font-normal text-ink-muted">
                / {{ intFmt.format(Math.round(result.metrics.rmse)) }}
              </span>
            </p>
          </div>
          <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
            <p class="text-[11px] text-ink-muted">sMAPE / MAPE</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums text-ink-primary">
              {{ decFmt.format(result.metrics.smape_pct) }}%
              <span class="text-xs font-normal text-ink-muted">
                / {{ decFmt.format(result.metrics.mape_pct) }}%
              </span>
            </p>
          </div>
          <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
            <p class="text-[11px] text-ink-muted">Mean Bias (MBE)</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums text-ink-primary">
              {{ intFmt.format(Math.round(result.metrics.mbe)) }}
            </p>
          </div>
        </div>

        <p
          v-if="includesNrt"
          class="rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 text-xs leading-relaxed text-accent-bright"
        >
          Note: Including 2026 mixes the harmonized archive with unharmonized near-real-time worker
          data (which adds NOAA-21 and has gaps from Jan–Mar 2026), lowering holdout R² and
          inflating MAPE. Switch to <strong>2012 – 2025</strong> for a consistent VIIRS-era baseline.
        </p>

        <p role="status" class="text-sm text-ink-primary" :aria-busy="isLoading">
          {{ summaryText }}
        </p>

        <div
          :class="
            isLoading
              ? 'opacity-60 transition-opacity duration-200'
              : 'transition-opacity duration-200'
          "
        >
          <MonthlyForecastRenderer
            :train="result.train"
            :test="result.test"
            :future="result.future"
            :description="chartDescription"
          />
        </div>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show future horizon table ({{ result.future.length }} months)</span>
            <span class="hidden group-open:inline">Hide future horizon table</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[32rem] text-left text-xs tabular-nums">
              <thead class="border-b border-border-subtle text-ink-muted">
                <tr>
                  <th class="py-2 pr-4 font-medium">Month</th>
                  <th class="py-2 pr-4 text-right font-medium">Forecast</th>
                  <th class="py-2 pr-4 text-right font-medium">80% CI</th>
                  <th class="py-2 text-right font-medium">95% CI</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="pt in result.future"
                  :key="pt.month"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-mono font-medium text-ink-primary">
                    {{ pt.month }}
                  </th>
                  <td class="py-2 pr-4 text-right text-accent-bright">
                    {{ intFmt.format(Math.round(pt.predicted)) }}
                  </td>
                  <td class="py-2 pr-4 text-right">
                    {{ intFmt.format(Math.round(pt.lower_80)) }} – {{ intFmt.format(Math.round(pt.upper_80)) }}
                  </td>
                  <td class="py-2 text-right">
                    {{ intFmt.format(Math.round(pt.lower_95)) }} – {{ intFmt.format(Math.round(pt.upper_95)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
