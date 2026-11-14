<script setup lang="ts">
import { MapPin, Pentagon } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseMapPanel from '@/components/ui/BaseMapPanel.vue'
import HotspotFilters from './HotspotFilters.vue'

defineProps<{ areaKm2: number | null }>()
const open = defineModel<boolean>('open', { required: true })
const { stats } = storeToRefs(useHotspotsStore())
</script>

<template>
  <BaseMapPanel v-model:open="open" title="Fire Activity">
    <div class="space-y-5 p-4">
      <div class="flex items-center gap-2 text-xs text-neutral-300">
        <Pentagon v-if="areaKm2 !== null" aria-hidden="true" class="h-3.5 w-3.5 text-neutral-500" />
        <MapPin v-else aria-hidden="true" class="h-3.5 w-3.5 text-neutral-500" />
        <span>{{ areaKm2 !== null ? 'Selected area' : 'Nicaragua' }}</span>
        <span v-if="areaKm2 !== null" class="ml-auto font-mono text-neutral-400"
          >{{ areaKm2.toLocaleString() }} km²</span
        >
      </div>
      <div
        class="grid grid-cols-2 gap-3 border-b border-white/10 pb-5"
        role="status"
        aria-label="Filtered hotspot metrics"
      >
        <div>
          <p class="mb-1 text-xs text-neutral-400">Hotspots</p>
          <p class="font-mono text-2xl font-semibold tabular-nums text-red-400">
            {{ stats.total.toLocaleString() }}
          </p>
        </div>
        <div>
          <p class="mb-1 text-xs text-neutral-400">Average FRP</p>
          <p class="font-mono text-2xl font-semibold tabular-nums">
            {{ stats.avgFrp }}<span class="ml-1 text-xs font-normal text-neutral-500">MW</span>
          </p>
        </div>
      </div>
      <HotspotFilters />
    </div>
  </BaseMapPanel>
</template>
