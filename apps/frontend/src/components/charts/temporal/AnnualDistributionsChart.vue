<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { RotateCw } from '@lucide/vue'
import { useTemporalChartsApi } from '@/api'
import { useChartLifecycle } from '@/composables/useChartLifecycle'
import { useChartFiltersStore } from '@/stores/chartFilters'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import AnnualDistributionsRenderer, {
  VARIABLE_META,
  type DistributionVariable,
} from '@/components/common/AnnualDistributionsChart.vue'

const filtersStore = useChartFiltersStore()
const { metric, activePolygon } = storeToRefs(filtersStore)
const { getAnnualStats } = useTemporalChartsApi()

const VARIABLE_OPTIONS = [
  { value: 'frp', label: 'FRP (MW)' },
  { value: 'confidence', label: 'Confidence' },
  { value: 'bright_tir', label: 'TIR (K)' },
  { value: 'bright_mir', label: 'MIR (K)' },
] as const satisfies readonly { value: DistributionVariable; label: string }[]

const WINDOW_OPTIONS = [
  { value: '2021-2025', label: '2021 – 2025' },
  { value: '2016-2020', label: '2016 – 2020' },
  { value: '2012-2016', label: '2012 – 2016' },
  { value: '2001-2005', label: '2001 – 2005' },
  { value: '2021-2026', label: '2021 – 2026 (inc. NRT)' },
] as const

const selectedVariable = shallowRef<DistributionVariable>('frp')
const selectedWindow = shallowRef<string>('2021-2025')

const {
  data: result,
  isLoading,
  error,
  refresh,
} = useChartLifecycle({
  fetcher: () => {
    const [startStr, endStr] = selectedWindow.value.split('-')
    return getAnnualStats({
      include_distributions: true,
      high_value: 90,
      metric: metric.value,
      start_year: Number(startStr ?? 2021),
      end_year: Number(endStr ?? 2025),
      polygon: activePolygon.value,
    })
  },
  watchSources: [selectedWindow, activePolygon, metric],
})

const rows = computed(() =>
  (result.value?.rows ?? []).map((r) => ({
    ...r,
    frp: r.frp ?? null,
    confidence: r.confidence ?? null,
    bright_tir: r.bright_tir ?? null,
    bright_mir: r.bright_mir ?? null,
  })),
)
const isEmpty = computed(
  () => result.value !== null && rows.value.every((r) => r.total_hotspots === 0),
)
const meta = computed(() => VARIABLE_META[selectedVariable.value])
const numFmt = computed(
  () => new Intl.NumberFormat('en-US', { maximumFractionDigits: meta.value.digits }),
)

function fmt(val: number | null | undefined): string {
  return val === null || val === undefined ? '—' : numFmt.value.format(val)
}

const summaryText = computed(() => {
  const valid = rows.value.filter((r) => (r[selectedVariable.value]?.count ?? 0) > 0)
  if (valid.length === 0) return 'No observations available for this variable and period.'
  const peak = [...valid].sort(
    (a, b) => (b[selectedVariable.value]?.median ?? 0) - (a[selectedVariable.value]?.median ?? 0),
  )[0]!
  const stat = peak[selectedVariable.value]!
  return `Highest median ${meta.value.label} in this window occurred in ${peak.year} at ${fmt(stat.median)} ${meta.value.unit} (IQR ${fmt(stat.p25)}–${fmt(stat.p75)} ${meta.value.unit}, P90 ${fmt(stat.p90)} ${meta.value.unit}).`
})

const chartDescription = computed(
  () => `Yearly distribution chart for ${meta.value.label}. ${summaryText.value}`,
)
</script>

<template>
  <section aria-labelledby="annual-distributions-title">
    <header
      class="flex flex-col gap-4 border-b border-border-subtle p-5 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="max-w-[62ch]">
        <div class="flex flex-wrap items-center gap-2">
          <h2 id="annual-distributions-title" class="text-base font-semibold text-ink-primary">
            Annual thermal &amp; confidence distributions
          </h2>
          <span
            class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 text-[11px] text-ink-muted"
          >
            Physical sensor values · high_value=90
          </span>
        </div>
        <p class="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          Exact SQL percentiles (<code class="font-mono text-xs text-ink-secondary">PERCENTILE_CONT</code>)
          for Fire Radiative Power, confidence, and brightness temperatures (TIR/MIR). Respects the
          exact drawn polygon in PostGIS.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <BaseToggleGroup
          v-model="selectedVariable"
          :options="VARIABLE_OPTIONS"
          label="Distribution variable"
        />
        <BaseSelect
          v-model="selectedWindow"
          :options="WINDOW_OPTIONS"
          label="Year window"
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
        <span>Could not load annual distributions. {{ error }}</span>
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
        class="h-[21rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse"
        aria-hidden="true"
      />

      <p
        v-else-if="isEmpty"
        class="rounded-lg border border-dashed border-border-strong px-4 py-10 text-center text-[13px] text-ink-muted"
      >
        No hotspot records are loaded for this selection yet.
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
          <AnnualDistributionsRenderer
            :rows="rows"
            :variable="selectedVariable"
            :description="chartDescription"
          />
        </div>

        <ul
          class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-secondary"
          aria-label="Chart legend"
        >
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-3 rounded-sm bg-accent" />
            Median (P50)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-5 border-t-2 border-dashed border-telemetry" />
            Mean
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="h-3 w-4 rounded-sm bg-accent/25" />
            IQR (P25–P75)
          </li>
          <li class="inline-flex items-center gap-2">
            <span class="w-4 border-t border-dotted border-amber-300" />
            90th percentile (P90)
          </li>
        </ul>

        <details class="group rounded-lg border border-border-subtle">
          <summary
            class="cursor-pointer list-none rounded-lg px-4 py-3 text-xs font-medium text-ink-secondary hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <span class="group-open:hidden">Show yearly percentile table</span>
            <span class="hidden group-open:inline">Hide yearly percentile table</span>
          </summary>
          <div class="overflow-x-auto border-t border-border-subtle px-4 pb-3">
            <table class="w-full min-w-[34rem] text-left text-xs">
              <thead class="border-b border-border-subtle text-ink-muted">
                <tr>
                  <th class="py-2 pr-3 font-medium">Year</th>
                  <th class="px-2 py-2 text-right font-medium">Count</th>
                  <th class="px-2 py-2 text-right font-medium">P25</th>
                  <th class="px-2 py-2 text-right font-medium">Median</th>
                  <th class="px-2 py-2 text-right font-medium">Mean</th>
                  <th class="px-2 py-2 text-right font-medium">P75</th>
                  <th class="px-2 py-2 text-right font-medium">P90</th>
                  <th class="pl-2 py-2 text-right font-medium">IQR</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-subtle text-ink-secondary">
                <tr v-for="row in rows" :key="row.year">
                  <td class="py-1.5 pr-3 font-medium text-ink-primary">{{ row.year }}</td>
                  <td class="px-2 py-1.5 text-right tabular-nums">
                    {{ (row[selectedVariable]?.count ?? 0).toLocaleString() }}
                  </td>
                  <td class="px-2 py-1.5 text-right tabular-nums">{{ fmt(row[selectedVariable]?.p25) }}</td>
                  <td class="px-2 py-1.5 text-right tabular-nums">{{ fmt(row[selectedVariable]?.median) }}</td>
                  <td class="px-2 py-1.5 text-right tabular-nums">{{ fmt(row[selectedVariable]?.mean) }}</td>
                  <td class="px-2 py-1.5 text-right tabular-nums">{{ fmt(row[selectedVariable]?.p75) }}</td>
                  <td class="px-2 py-1.5 text-right tabular-nums">{{ fmt(row[selectedVariable]?.p90) }}</td>
                  <td class="pl-2 py-1.5 text-right tabular-nums">{{ fmt(row[selectedVariable]?.iqr) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </template>
    </div>
  </section>
</template>
