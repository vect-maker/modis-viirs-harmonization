<script lang="ts">
export type StatsSectionId =
  | 'all'
  | 'overview'
  | 'distributions'
  | 'fire-calendar'
  | 'spatial'
  | 'diagnostics'
  | 'forecast'
  | 'movement'
  | 'weather'

export interface StatsSectionItem {
  id: StatsSectionId
  label: string
  shortLabel: string
  endpoints: readonly string[]
  description: string
}

export const STATS_SECTIONS: readonly StatsSectionItem[] = [
  {
    id: 'all',
    label: 'All Statistics & Endpoints',
    shortLabel: 'All Charts (13)',
    endpoints: ['/charts/temporal/*', '/charts/diagnostics/*', '/charts/models/*', '/weather'],
    description: 'All temporal, diagnostic, spatial, ML movement, and NASA POWER weather charts.',
  },
  {
    id: 'overview',
    label: 'Monthly & Annual Overview',
    shortLabel: 'Overview',
    endpoints: ['/charts/temporal/monthly-comparison', '/charts/temporal/annual-stats'],
    description: 'Monthly anomaly baseline and multi-year harmonized activity.',
  },
  {
    id: 'distributions',
    label: 'Annual Distributions',
    shortLabel: 'Distributions',
    endpoints: ['/charts/temporal/annual-stats?include_distributions=true'],
    description: 'Yearly quartiles, median, P90, and IQR for FRP, confidence, and brightness.',
  },
  {
    id: 'fire-calendar',
    label: 'Fire Calendar',
    shortLabel: 'Fire Calendar',
    endpoints: ['/charts/temporal/fire-calendar'],
    description: 'Aggregated hotspots, radiative power (FRP), and day/night split by period.',
  },
  {
    id: 'spatial',
    label: 'Spatial Density & Anomalies',
    shortLabel: 'Spatial',
    endpoints: ['/charts/diagnostics/spatial-density', '/charts/diagnostics/spatial-anomalies'],
    description: 'SQL grid cell density and IsolationForest spatial outlier detection.',
  },
  {
    id: 'diagnostics',
    label: 'Correlations & Confidence DBSCAN',
    shortLabel: 'Correlations & DBSCAN',
    endpoints: ['/charts/diagnostics/correlations', '/charts/diagnostics/confidence-dbscan'],
    description: 'Pearson r / R² matrix across thermal variables and confidence value clustering.',
  },
  {
    id: 'forecast',
    label: 'Seasonal Forecast',
    shortLabel: 'Forecast',
    endpoints: ['/charts/models/monthly-forecast'],
    description: 'Autoregressive Ridge monthly forecast with 80% and 95% confidence bands.',
  },
  {
    id: 'movement',
    label: 'Cluster Movement & ML Prediction',
    shortLabel: 'Movement & ML',
    endpoints: ['/charts/models/cluster-movement', '/charts/models/predict'],
    description: 'Spatio-temporal DBSCAN trajectories and RandomForest displacement prediction.',
  },
  {
    id: 'weather',
    label: 'Weather & Wind Alignment',
    shortLabel: 'Weather',
    endpoints: ['/charts/models/weather-correlation', '/weather'],
    description: 'NASA POWER daily meteorology and wind-to-fire vector alignment.',
  },
] as const
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { ChevronRight, Home } from '@lucide/vue'

const props = defineProps<{
  sections?: readonly StatsSectionItem[]
}>()

const model = defineModel<StatsSectionId>({ required: true })

const items = computed(() => props.sections ?? STATS_SECTIONS)
const activeSection = computed(
  () => items.value.find((item) => item.id === model.value) ?? items.value[0]!,
)
</script>

<template>
  <nav
    aria-label="Statistics breadcrumb and sections"
    class="border-b border-border-subtle bg-surface-base/40 px-5 py-3"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <ol class="flex flex-wrap items-center gap-1.5 text-xs">
        <li>
          <button
            type="button"
            class="inline-flex cursor-pointer items-center gap-1.5 rounded px-1.5 py-0.5 font-medium text-ink-muted transition-colors hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
            @click="model = 'all'"
          >
            <Home aria-hidden="true" class="h-3.5 w-3.5 text-accent" />
            <span>Statistics</span>
          </button>
        </li>
        <li aria-hidden="true" class="text-ink-muted/60">
          <ChevronRight class="h-3.5 w-3.5" />
        </li>
        <li aria-current="page" class="font-semibold text-ink-primary">
          {{ activeSection.label }}
        </li>
      </ol>

      <div class="flex flex-wrap items-center gap-1.5">
        <code
          v-for="ep in activeSection.endpoints"
          :key="ep"
          class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 font-mono text-[11px] text-ink-secondary"
        >
          {{ ep }}
        </code>
      </div>
    </div>

    <div
      role="tablist"
      aria-label="Statistics categories"
      class="mt-2.5 flex flex-wrap gap-1.5"
    >
      <button
        v-for="section in items"
        :key="section.id"
        type="button"
        role="tab"
        :aria-selected="model === section.id"
        class="min-h-8 shrink-0 cursor-pointer rounded-lg border px-3 py-1 text-xs font-medium transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-focus"
        :class="
          model === section.id
            ? 'border-accent/50 bg-accent/15 text-accent-bright'
            : 'border-border-subtle bg-surface-input text-ink-muted hover:border-border-strong hover:text-ink-primary'
        "
        @click="model = section.id"
      >
        {{ section.shortLabel }}
      </button>
    </div>
  </nav>
</template>
