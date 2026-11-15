<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { RotateCw } from '@lucide/vue'
import { z } from 'zod'
import type { GeoJSONPolygon } from 'zod-geojson'
import { useApiFetch } from '@/api/useApiFetch'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import MonthlyForecastChart from '@/components/common/MonthlyForecastChart.vue'

const props = defineProps<{
  polygon?: GeoJSONPolygon | null
  metric?: 'raw' | 'harmonized'
}>()

const TrainSchema = z.object({
  month: z.string(),
  actual: z.number().int().nonnegative(),
})

const TestSchema = z.object({
  month: z.string(),
  actual: z.number().int().nonnegative(),
  predicted: z.number(),
  lower_80: z.number(),
  upper_80: z.number(),
  lower_95: z.number(),
  upper_95: z.number(),
})

const FutureSchema = z.object({
  month: z.string(),
  predicted: z.number(),
  lower_80: z.number(),
  upper_80: z.number(),
  lower_95: z.number(),
  upper_95: z.number(),
})

const ResponseSchema = z.object({
  metrics: z.object({
    total_months: z.number().int(),
    train_months: z.number().int(),
    test_months: z.number().int(),
    mae: z.number(),
    mse: z.number(),
    rmse: z.number(),
    mape_pct: z.number(),
    smape_pct: z.number(),
    r2: z.number(),
    mbe: z.number(),
    residual_std: z.number(),
  }),
  train: z.array(TrainSchema),
  test: z.array(TestSchema),
  future: z.array(FutureSchema),
})
type ForecastResponse = z.infer<typeof ResponseSchema>

const HORIZON_OPTIONS = [
  { value: '6', label: '6 months' },
  { value: '12', label: '12 months' },
  { value: '18', label: '18 months' },
] as const

const RANGE_OPTIONS = [
  { value: '2012-2025', label: '2012 – 2025 (VIIRS archive)' },
  { value: '2001-2025', label: '2001 – 2025 (Full archive)' },
  { value: '2001-2026', label: '2001 – 2026 (Includes NRT)' },
] as const

const futureMonths = shallowRef<'6' | '12' | '18'>('6')
const trainingRange = shallowRef<string>('2012-2025')
const result = shallowRef<ForecastResponse | null>(null)
const isLoading = shallowRef(false)
const error = shallowRef<string | null>(null)
let latestRequest = 0

async function load() {
  const requestId = ++latestRequest
  isLoading.value = true
  error.value = null

  const [startStr, endStr] = trainingRange.value.split('-')
  const params = new URLSearchParams({
    train_ratio: '0.8',
    future_months: futureMonths.value,
    start_year: startStr ?? '2012',
    end_year: endStr ?? '2025',
    metric: props.metric ?? 'raw',
  })
  if (props.polygon) {
    params.set('polygon', JSON.stringify(props.polygon))
  }

  const { data, error: fetchError } = await useApiFetch(
    `/dashboard/monthly-forecast?${params.toString()}`,
  )
    .get()
    .json()

  if (requestId !== latestRequest) return
  try {
    if (fetchError.value || !data.value) {
      throw fetchError.value ?? new Error('The server returned no data.')
    }
    result.value = ResponseSchema.parse(data.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error.'
  } finally {
    isLoading.value = false
  }
}

watch([futureMonths, trainingRange, () => props.polygon, () => props.metric], load, {
  immediate: true,
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
            {{ polygon ? 'Drawn area (Polygon)' : 'All regions' }} ·
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
          @click="load"
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
          <MonthlyForecastChart
            :train="result.train"
            :test="result.test"
            :future="result.future"
            :description="chartDescription"
          />
        </div>

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          aria-label="Chart legend"
        >
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-2 border-ink-secondary" />
            Observed detections
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-2 border-dashed border-accent" />
            Predicted (Holdout &amp; Future)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-5 rounded-sm bg-accent/20 ring-1 ring-accent/40" />
            80% confidence band
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-5 rounded-sm bg-telemetry/15 ring-1 ring-telemetry/30" />
            95% confidence band
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">
              Show future forecast table ({{ result.future.length }} months)
            </span>
            <span class="hidden group-open:inline">Hide future forecast table</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[34rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Projected monthly hotspot detections with 80% and 95% confidence intervals
              </caption>
              <thead class="text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Future Month</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Predicted</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">80% Confidence Interval</th>
                  <th scope="col" class="py-2 text-right font-medium">95% Confidence Interval</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="row in result.future"
                  :key="row.month"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-mono font-medium text-ink-primary">
                    {{ row.month }}
                  </th>
                  <td class="py-2 pr-4 text-right font-mono text-accent-bright">
                    {{ intFmt.format(Math.round(row.predicted)) }}
                  </td>
                  <td class="py-2 pr-4 text-right">
                    {{ intFmt.format(Math.round(row.lower_80)) }} to
                    {{ intFmt.format(Math.round(row.upper_80)) }}
                  </td>
                  <td class="py-2 text-right">
                    {{ intFmt.format(Math.round(row.lower_95)) }} to
                    {{ intFmt.format(Math.round(row.upper_95)) }}
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
