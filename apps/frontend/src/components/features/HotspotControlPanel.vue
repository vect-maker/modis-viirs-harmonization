<script setup lang="ts">
import { MapPin, Pentagon } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseMapPanel from '@/components/ui/BaseMapPanel.vue'
import HotspotFilters from './HotspotFilters.vue'
import HotspotCsvExport from './HotspotCsvExport.vue'

defineProps<{ areaKm2: number | null }>()
const open = defineModel<boolean>('open', { required: true })
const { stats } = storeToRefs(useHotspotsStore())
</script>

<template>
  <BaseMapPanel v-model:open="open" title="Fire Activity">
    <div class="space-y-4 p-4">
      <div class="flex items-center gap-2 text-xs text-neutral-300">
        <Pentagon v-if="areaKm2 !== null" aria-hidden="true" class="h-3.5 w-3.5 text-neutral-500" />
        <MapPin v-else aria-hidden="true" class="h-3.5 w-3.5 text-neutral-500" />
        <span>{{ areaKm2 !== null ? 'Selected area' : 'Nicaragua' }}</span>
        <span v-if="areaKm2 !== null" class="ml-auto font-mono text-neutral-400"
          >{{ areaKm2.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} km²</span
        >
      </div>
      <div class="grid grid-cols-2 gap-2.5" role="status" aria-label="Filtered hotspot metrics">
        <div class="rounded-lg border border-white/5 bg-white/[0.035] p-3">
          <p class="mb-2 text-[11px] text-neutral-400">Hotspots</p>
          <p class="font-mono text-[26px] leading-none font-medium tabular-nums text-red-400">
            {{ stats.total.toLocaleString() }}
          </p>
        </div>
        <div class="rounded-lg border border-white/5 bg-white/[0.035] p-3">
          <p class="mb-2 text-[11px] text-neutral-400">Average FRP</p>
          <p class="font-mono text-[26px] leading-none font-medium tabular-nums">
            {{ stats.avgFrp }}<span class="ml-1 text-xs font-normal text-neutral-500">MW</span>
          </p>
        </div>
      </div>
      <HotspotFilters />
      <HotspotCsvExport />
      <p class="border-t border-white/10 pt-3 text-[10px] leading-relaxed text-neutral-500">
        Imagery: Esri, Maxar, Earthstar Geographics ·
        <a href="https://maplibre.org/" target="_blank" rel="noopener noreferrer" class="rounded hover:text-neutral-300 focus-visible:outline-2 focus-visible:outline-red-400">MapLibre</a>
      </p>
    </div>
  </BaseMapPanel>
</template>
