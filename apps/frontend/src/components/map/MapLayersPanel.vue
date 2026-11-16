<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { Check, ChevronDown, Flame, Hexagon, Layers } from '@lucide/vue'
import { CheckboxIndicator, CheckboxRoot } from 'reka-ui'
import { useI18n } from 'vue-i18n'
import { useLocaleFormatters } from '@/i18n'
import { useClustersStore } from '@/stores/clusters'
import { useHotspotsStore } from '@/stores/hotspots'

const { t } = useI18n()
const { formatInt } = useLocaleFormatters()
const clustersStore = useClustersStore()
const hotspotsStore = useHotspotsStore()
const { fireEvents, showEvents, showHotspots } = storeToRefs(clustersStore)
const { filteredHotspots } = storeToRefs(hotspotsStore)

const expanded = shallowRef(true)

const activeCount = computed(() => (showEvents.value ? 1 : 0) + (showHotspots.value ? 1 : 0))
</script>

<template>
  <section
    :aria-label="t('map.layers.aria')"
    class="w-64 overflow-hidden rounded-xl border border-border-strong bg-surface-panel/92 shadow-[0_8px_28px_rgba(0,0,0,0.45)] backdrop-blur-md"
  >
    <button
      type="button"
      :aria-expanded="expanded"
      aria-controls="map-layers-body"
      class="flex w-full cursor-pointer items-center justify-between gap-2.5 px-3.5 py-2.5 text-left text-xs font-semibold text-ink-primary transition-colors hover:bg-white/[0.04] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus"
      @click="expanded = !expanded"
    >
      <span class="flex items-center gap-2">
        <Layers aria-hidden="true" class="size-3.5 text-accent-bright" />
        <span>{{ t('map.layers.title') }}</span>
        <span
          class="rounded-full border border-border-subtle bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] font-medium tabular-nums text-ink-secondary"
        >
          {{ activeCount }}/2
        </span>
      </span>
      <ChevronDown
        aria-hidden="true"
        class="size-3.5 text-ink-muted transition-transform duration-200"
        :class="expanded ? 'rotate-180' : ''"
      />
    </button>

    <div
      id="map-layers-body"
      v-show="expanded"
      class="space-y-1.5 border-t border-border-subtle p-2"
    >
      <label
        class="flex cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2 transition-colors hover:bg-white/[0.04]"
      >
        <CheckboxRoot
          :model-value="showEvents"
          :aria-label="t('map.layers.toggleEventsAria')"
          class="flex size-4 shrink-0 items-center justify-center rounded border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          :class="
            showEvents
              ? 'border-accent bg-accent text-surface-base'
              : 'border-border-strong bg-surface-base/70 text-transparent'
          "
          @update:model-value="(val) => clustersStore.setLayerVisible('events', val === true)"
        >
          <CheckboxIndicator class="flex items-center justify-center">
            <Check class="size-3" :stroke-width="3" aria-hidden="true" />
          </CheckboxIndicator>
        </CheckboxRoot>

        <span
          class="flex size-6 shrink-0 items-center justify-center rounded-md border border-orange-400/35 bg-orange-500/15 text-orange-300"
          aria-hidden="true"
        >
          <Hexagon class="size-3.5" />
        </span>

        <span class="min-w-0 flex-1">
          <span class="block text-xs font-medium leading-tight text-ink-primary">{{
            t('map.layers.fireEvents')
          }}</span>
          <span class="block truncate text-[10px] text-ink-muted">{{
            t('map.layers.eventPerimeters')
          }}</span>
        </span>

        <span
          class="shrink-0 font-mono text-[11px] font-medium tabular-nums text-ink-secondary"
        >
          {{ formatInt(fireEvents.features.length) }}
        </span>
      </label>

      <label
        class="flex cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2 transition-colors hover:bg-white/[0.04]"
      >
        <CheckboxRoot
          :model-value="showHotspots"
          :aria-label="t('map.layers.toggleHotspotsAria')"
          class="flex size-4 shrink-0 items-center justify-center rounded border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          :class="
            showHotspots
              ? 'border-accent bg-accent text-surface-base'
              : 'border-border-strong bg-surface-base/70 text-transparent'
          "
          @update:model-value="(val) => clustersStore.setLayerVisible('hotspots', val === true)"
        >
          <CheckboxIndicator class="flex items-center justify-center">
            <Check class="size-3" :stroke-width="3" aria-hidden="true" />
          </CheckboxIndicator>
        </CheckboxRoot>

        <span
          class="flex size-6 shrink-0 items-center justify-center rounded-md border border-amber-400/35 bg-amber-500/15 text-amber-300"
          aria-hidden="true"
        >
          <Flame class="size-3.5" />
        </span>

        <span class="min-w-0 flex-1">
          <span class="block text-xs font-medium leading-tight text-ink-primary">{{
            t('map.layers.hotspots')
          }}</span>
          <span class="block truncate text-[10px] text-ink-muted">{{
            t('map.layers.modisViirsPoints')
          }}</span>
        </span>

        <span
          class="shrink-0 font-mono text-[11px] font-medium tabular-nums text-ink-secondary"
        >
          {{ formatInt(filteredHotspots.length) }}
        </span>
      </label>
    </div>
  </section>
</template>
