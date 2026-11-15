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
  <BaseMapPanel v-model:open="open" title="PyroTrace · Fire Activity" home-to="/">
    <div class="space-y-4 p-4">
      <div class="flex items-center gap-2 text-xs text-ink-secondary">
        <Pentagon v-if="areaKm2 !== null" aria-hidden="true" class="h-3.5 w-3.5 text-ink-muted" />
        <MapPin v-else aria-hidden="true" class="h-3.5 w-3.5 text-ink-muted" />
        <span>{{ areaKm2 !== null ? 'Selected area' : 'Nicaragua' }}</span>
        <span v-if="areaKm2 !== null" class="ml-auto font-mono text-ink-muted"
          >{{ areaKm2.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} km²</span
        >
      </div>
      <div class="grid grid-cols-2 gap-2.5" role="status" aria-label="Filtered hotspot metrics">
        <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
          <p class="mb-2 text-[11px] text-ink-muted">Hotspots</p>
          <p class="font-mono text-[26px] leading-none font-medium tabular-nums text-accent-bright">
            {{ stats.total.toLocaleString() }}
          </p>
        </div>
        <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-3">
          <p class="mb-2 text-[11px] text-ink-muted">Average FRP</p>
          <p class="font-mono text-[26px] leading-none font-medium tabular-nums text-ink-primary">
            {{ stats.avgFrp }}<span class="ml-1 text-xs font-normal text-ink-muted">MW</span>
          </p>
        </div>
      </div>
      <HotspotFilters />
      <HotspotCsvExport />
    </div>
  </BaseMapPanel>
</template>
