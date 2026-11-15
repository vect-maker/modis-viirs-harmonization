<script setup lang="ts">
import { BookOpen } from '@lucide/vue'
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'
import DashboardGuideDiagram, {
  type GuideDiagramVariant,
} from '@/components/common/DashboardGuideDiagram.vue'

const GUIDE_CARDS: ReadonlyArray<{
  variant: GuideDiagramVariant
  title: string
  description: string
}> = [
  {
    variant: 'layers',
    title: '1. Map Layers',
    description: 'Check Fire Events for clustered perimeters or Hotspots for raw detections.',
  },
  {
    variant: 'aoi',
    title: '2. Area & Filters',
    description: 'Draw an area on the map or pick dates and sensors to update metrics and CSV.',
  },
  {
    variant: 'timeline',
    title: '3. Activity Timeline',
    description: 'Click any daily bar to filter by UTC day, or switch to Historical for 2000–2026.',
  },
  {
    variant: 'stats',
    title: '4. Statistics',
    description: 'Open Statistics for annual distributions, weather correlations, and forecasts.',
  },
]
</script>

<template>
  <PopoverRoot>
    <PopoverTrigger as-child>
      <button
        type="button"
        aria-label="Open dashboard visual guide"
        class="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border border-border-subtle bg-surface-raised px-3 py-2 text-[13px] font-medium text-ink-secondary transition hover:border-border-strong hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      >
        <BookOpen aria-hidden="true" class="h-3.5 w-3.5 text-accent-bright" />
        <span class="hidden sm:inline">Guide</span>
      </button>
    </PopoverTrigger>

    <PopoverPortal>
      <PopoverContent
        side="bottom"
        align="end"
        :side-offset="10"
        :collision-padding="16"
        class="z-50 w-[min(36rem,calc(100vw-2rem))] rounded-2xl border border-border-strong bg-surface-panel/95 p-4 text-xs text-ink-primary shadow-2xl backdrop-blur-md"
      >
        <div class="mb-3 flex items-center justify-between gap-2">
          <div>
            <h2 class="text-sm font-semibold text-ink-primary">How to use PyroTrace</h2>
            <p class="text-[11px] text-ink-muted">
              Explore active fires on the map and inspect temporal, spatial, and weather patterns.
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          <div
            v-for="card in GUIDE_CARDS"
            :key="card.variant"
            class="rounded-xl border border-border-subtle bg-surface-base/75 p-2.5"
          >
            <DashboardGuideDiagram :variant="card.variant" />
            <p class="mt-2 text-xs font-semibold text-ink-primary">{{ card.title }}</p>
            <p class="mt-0.5 text-[11px] leading-snug text-ink-secondary">{{ card.description }}</p>
          </div>
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
