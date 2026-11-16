<script lang="ts">
export type StatsSectionId =
  | 'all'
  | 'overview'
  | 'distributions'
  | 'fire-calendar'
  | 'spatial'
  | 'diagnostics'
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
    shortLabel: 'All Charts (9)',
    endpoints: ['/charts/temporal/*', '/charts/diagnostics/*', '/charts/models/weather-correlation', '/weather'],
    description: 'All temporal, diagnostic, spatial, and NASA POWER weather charts.',
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
    label: 'Correlations',
    shortLabel: 'Correlations',
    endpoints: ['/charts/diagnostics/correlations'],
    description: 'Pearson r / R² matrix across thermal variables.',
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

const props = defineProps<{
  sections?: readonly StatsSectionItem[]
}>()

const model = defineModel<StatsSectionId>({ required: true })

const items = computed(() => props.sections ?? STATS_SECTIONS)
</script>

<template>
  <nav
    aria-label="Statistics sections"
    class="border-b border-border-subtle bg-surface-base/40 px-5 py-3"
  >
    <div
      role="tablist"
      aria-label="Statistics categories"
      class="flex flex-wrap gap-1.5"
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
