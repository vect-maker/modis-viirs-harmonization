<script setup lang="ts">
import { computed } from 'vue'
import { CircleHelp, Flame, Hexagon, LocateFixed } from '@lucide/vue'
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'
import { useI18n } from 'vue-i18n'
import DashboardGuideDiagram from '@/components/common/DashboardGuideDiagram.vue'

const { t } = useI18n()

const CONFIDENCE_ITEMS = computed(() => [
  {
    key: 'high',
    label: t('map.legend.high'),
    description: t('map.legend.highDesc'),
    fill: '#ef4444',
    stroke: '#fef08a',
  },
  {
    key: 'nominal',
    label: t('map.legend.nominal'),
    description: t('map.legend.nominalDesc'),
    fill: '#f97316',
    stroke: '#fed7aa',
  },
  {
    key: 'low',
    label: t('map.legend.low'),
    description: t('map.legend.lowDesc'),
    fill: '#eab308',
    stroke: '#fef9c3',
  },
  {
    key: 'unknown',
    label: t('map.legend.unclassified'),
    description: t('map.legend.unclassifiedDesc'),
    fill: '#94a3b8',
    stroke: '#e2e8f0',
  },
])
</script>

<template>
  <PopoverRoot>
    <PopoverTrigger as-child>
      <button
        type="button"
        :aria-label="t('map.legend.aria')"
        :title="t('map.legend.aria')"
        class="inline-flex size-[29px] cursor-pointer items-center justify-center rounded-[10px] border border-border-strong bg-surface-panel/92 text-ink-secondary shadow-[0_4px_12px_#0004] backdrop-blur-md transition-colors hover:bg-surface-elevated hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      >
        <CircleHelp class="size-4" aria-hidden="true" />
      </button>
    </PopoverTrigger>

    <PopoverPortal>
      <PopoverContent
        side="bottom"
        align="start"
        :side-offset="8"
        class="z-50 w-68 rounded-xl border border-border-strong bg-surface-panel/95 p-3.5 text-xs text-ink-primary shadow-2xl backdrop-blur-md"
      >
        <p class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
          {{ t('map.legend.howLayers') }}
        </p>
        <div class="mt-2 overflow-hidden rounded-lg border border-border-subtle bg-surface-base/80 p-1.5">
          <DashboardGuideDiagram variant="layers" />
        </div>

        <div class="my-2.5 border-t border-border-subtle" />

        <p class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
          {{ t('map.legend.fireEvents') }}
        </p>
        <div class="mt-2 flex items-center gap-2.5">
          <span
            class="flex size-6 shrink-0 items-center justify-center rounded-md border border-orange-400/35 bg-orange-500/15 text-orange-300"
          >
            <Hexagon class="size-3.5" aria-hidden="true" />
          </span>
          <div class="min-w-0">
            <div class="font-medium text-ink-primary">{{ t('map.legend.eventPerimeter') }}</div>
            <div class="text-[11px] text-ink-muted">
              {{ t('map.legend.eventGrouping') }}
            </div>
          </div>
        </div>

        <div class="my-2.5 border-t border-border-subtle" />

        <p class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
          {{ t('map.legend.hotspotConfidence') }}
        </p>
        <ul class="mt-2 space-y-2">
          <li v-for="item in CONFIDENCE_ITEMS" :key="item.key" class="flex items-center gap-2.5">
            <span
              class="flex size-6 shrink-0 items-center justify-center rounded-md border border-border-subtle bg-surface-elevated/80"
            >
              <Flame
                class="size-4"
                :color="item.stroke"
                :fill="item.fill"
                :stroke-width="2"
                aria-hidden="true"
              />
            </span>
            <div class="min-w-0">
              <div class="font-medium text-ink-primary">{{ item.label }}</div>
              <div class="text-[11px] text-ink-muted">{{ item.description }}</div>
            </div>
          </li>
        </ul>

        <div class="my-2.5 border-t border-border-subtle" />

        <p class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
          {{ t('map.legend.positionMarker') }}
        </p>
        <div class="mt-2 flex items-center gap-2.5">
          <span
            class="flex size-6 shrink-0 items-center justify-center rounded-full border-2 border-white bg-sky-500 text-white shadow-[0_0_8px_rgba(56,189,248,0.65)]"
          >
            <LocateFixed class="size-3.5" :stroke-width="2.25" aria-hidden="true" />
          </span>
          <div class="min-w-0">
            <div class="font-medium text-ink-primary">{{ t('map.legend.yourLocation') }}</div>
            <div class="text-[11px] text-ink-muted">{{ t('map.legend.gpsPosition') }}</div>
          </div>
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
