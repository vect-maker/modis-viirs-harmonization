<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { useDiagnosticChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useChartFiltersStore } from '@/stores/chartFilters'
import BaseChartLoading from '@/components/ui/BaseChartLoading.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import CorrelationsRenderer, { CORR_LABELS } from '@/components/common/CorrelationsChart.vue'

const filtersStore = useChartFiltersStore()
const { metric, activePolygon, selectedYear: storeYear } = storeToRefs(filtersStore)
const { getCorrelations } = useDiagnosticChartsApi()

const selectedYear = computed<number>({
  get: () => storeYear.value,
  set: (value) => filtersStore.setSelectedYear(value),
})

const STAT_OPTIONS = [
  { value: 'pearson_r', label: 'Pearson r' },
  { value: 'r2', label: 'R² (Variance)' },
] as const

const YEAR_OPTIONS = Array.from({ length: 26 }, (_, idx) => {
  const year = 2026 - idx
  return { value: year, label: String(year) }
})

const statMode = shallowRef<'pearson_r' | 'r2'>('pearson_r')

const {
  data: result,
  isLoading,
  error,
  refresh,
} = useChartLifecycle({
  fetcher: () =>
    getCorrelations({
      high_value: 90,
      metric: metric.value,
      start_date: `${selectedYear.value}-01-01`,
      end_date: `${selectedYear.value}-12-31`,
      polygon: activePolygon.value,
    }),
  watchSources: [selectedYear, activePolygon, metric],
})

const pairs = computed(() => result.value ?? [])
const isEmpty = computed(() => result.value !== null && pairs.value.every((p) => p.n < 2))

const summaryText = computed(() => {
  const valid = pairs.value.filter((p) => p.pearson_r !== null)
  if (valid.length === 0) return 'Insufficient paired observations to compute correlations.'
  const strongest = [...valid].sort(
    (a, b) => Math.abs(b.pearson_r ?? 0) - Math.abs(a.pearson_r ?? 0),
  )[0]!
  const lx = CORR_LABELS[strongest.x] ?? strongest.x
  const ly = CORR_LABELS[strongest.y] ?? strongest.y
  return `Strongest correlation in ${selectedYear.value} is between ${lx} and ${ly} with Pearson r = ${(strongest.pearson_r ?? 0).toFixed(3)} (R² = ${(strongest.r2 ?? 0).toFixed(3)}, n = ${strongest.n.toLocaleString()}).`
})

const chartDescription = computed(
  () => `4x4 correlation matrix heatmap for FRP, confidence, TIR, and MIR. ${summaryText.value}`,
)
</script>

<template>
  <section aria-labelledby="correlations-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="correlations-title" class="text-base font-semibold text-ink-primary">
            Thermal &amp; confidence correlation matrix (Pearson r &amp; R²)
          </h2>
          <span
            class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 text-[11px] text-ink-muted"
          >
            {{ activePolygon ? 'Drawn area (Polygon)' : 'All regions' }} ·
            {{ metric === 'harmonized' ? 'Harmonized' : 'Raw' }} · high_value=90
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Computes exact pairwise Pearson correlation (<code class="font-mono text-xs">r</code>)
          and coefficient of determination (<code class="font-mono text-xs">R²</code>) in SQL
          between radiative power, confidence, and infrared brightness temperatures.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup v-model="statMode" :options="STAT_OPTIONS" label="Correlation metric" />
        <BaseSelect
          v-model="selectedYear"
          :options="YEAR_OPTIONS"
          label="Year"
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
        <span>Could not load correlations. {{ error }}</span>
        <button
          type="button"
          class="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-red-300/40 px-3 text-xs font-medium hover:bg-red-400/10 focus-visible:outline-2 focus-visible:outline-focus"
          @click="refresh"
        >
          <RotateCw aria-hidden="true" class="h-3.5 w-3.5" />
          Try again
        </button>
      </div>

      <BaseChartLoading
        v-if="result === null && isLoading"
        height-class="h-[20rem]"
        label="Loading correlations…"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        Not enough paired observations for {{ selectedYear }}.
      </p>

      <template v-else-if="result !== null">
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
          <CorrelationsRenderer
            :pairs="pairs"
            :stat-mode="statMode"
            :description="chartDescription"
          />
        </div>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show pairwise statistics table</span>
            <span class="hidden group-open:inline">Hide pairwise statistics table</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[36rem] text-left text-xs tabular-nums">
              <caption class="sr-only">
                Pairwise Pearson r and R² between thermal variables
              </caption>
              <thead class="text-ink-muted">
                <tr class="border-b border-border-subtle">
                  <th scope="col" class="py-2 pr-4 font-medium">Variable Pair</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Observations (n)</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Pearson r</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">R²</th>
                  <th scope="col" class="py-2 pr-4 text-right font-medium">Mean X</th>
                  <th scope="col" class="py-2 text-right font-medium">Mean Y</th>
                </tr>
              </thead>
              <tbody class="text-ink-secondary">
                <tr
                  v-for="pair in pairs"
                  :key="`${pair.x}-${pair.y}`"
                  class="border-b border-border-subtle/60 last:border-0"
                >
                  <th scope="row" class="py-2 pr-4 font-medium text-ink-primary">
                    {{ CORR_LABELS[pair.x] ?? pair.x }} × {{ CORR_LABELS[pair.y] ?? pair.y }}
                  </th>
                  <td class="py-2 pr-4 text-right">{{ pair.n.toLocaleString() }}</td>
                  <td class="py-2 pr-4 text-right font-mono text-accent-bright">
                    {{ pair.pearson_r?.toFixed(4) ?? '—' }}
                  </td>
                  <td class="py-2 pr-4 text-right font-mono">
                    {{ pair.r2?.toFixed(4) ?? '—' }}
                  </td>
                  <td class="py-2 pr-4 text-right">
                    {{ pair.mean_x?.toFixed(2) ?? '—' }}
                  </td>
                  <td class="py-2 text-right">
                    {{ pair.mean_y?.toFixed(2) ?? '—' }}
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
