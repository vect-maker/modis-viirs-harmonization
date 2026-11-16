<script lang="ts">
export type StatsSectionId =
  | 'seasonal'
  | 'annual'
  | 'archive'
  | 'fire-calendar'
  | 'intensity'
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
    id: 'seasonal',
    label: 'Seasonal Baseline Comparison',
    shortLabel: 'Seasonal Baseline',
    endpoints: ['/charts/temporal/monthly-comparison'],
    description:
      'Compare monthly burning activity in a selected year against the multi-year historical median and typical range.',
  },
  {
    id: 'annual',
    label: 'Multi-Year Burning Activity',
    shortLabel: 'Multi-Year Activity',
    endpoints: ['/charts/temporal/annual-stats'],
    description:
      'Compare annual fire activity from 2001 to present across harmonized MODIS-VIIRS index and raw detections.',
  },
  {
    id: 'archive',
    label: 'Historical Archive Calendar',
    shortLabel: 'Archive Heatmap',
    endpoints: ['/charts/temporal/historical-calendar'],
    description:
      'Browse 2001–2026 monthly archive counts by sensor and jump directly to a month on the map or compare a year.',
  },
  {
    id: 'fire-calendar',
    label: 'Burning Activity Calendar',
    shortLabel: 'Fire Calendar',
    endpoints: ['/charts/temporal/fire-calendar'],
    description:
      'Inspect monthly, weekly, or daily burning activity, daytime vs. nighttime overpasses, and radiative power.',
  },
  {
    id: 'intensity',
    label: 'Fire Radiative Power (FRP) Intensity',
    shortLabel: 'Fire Intensity (FRP)',
    endpoints: ['/charts/temporal/annual-stats?include_distributions=true'],
    description:
      'Track annual fire intensity distributions (median, interquartile range, and 90th percentile FRP in megawatts).',
  },
  {
    id: 'weather',
    label: 'Fire Weather & Wind Alignment',
    shortLabel: 'Fire Weather',
    endpoints: ['/charts/models/weather-correlation', '/weather'],
    description:
      'Analyze NASA POWER daily temperature, relative humidity, precipitation, and wind-to-fire spread alignment.',
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
