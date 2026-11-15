<script setup lang="ts">
import { computed } from 'vue'
import { MapPin, Pentagon } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { useHotspotsStore } from '@/stores/hotspots'
import { useClustersStore } from '@/stores/clusters'
import BaseMapPanel from '@/components/ui/BaseMapPanel.vue'
import BaseHelpGuidePopover from '@/components/ui/BaseHelpGuidePopover.vue'
import DashboardGuideDiagram from '@/components/common/DashboardGuideDiagram.vue'
import HotspotFilters from './HotspotFilters.vue'
import HotspotCsvExport from './HotspotCsvExport.vue'

defineProps<{ areaKm2: number | null }>()
const open = defineModel<boolean>('open', { required: true })
const { stats } = storeToRefs(useHotspotsStore())
const { fireEvents } = storeToRefs(useClustersStore())
const eventCount = computed(() => fireEvents.value.features.length)
</script>

<template>
  <BaseMapPanel v-model:open="open" title="Fire Activity">
    <div class="space-y-3.5 p-3.5">
      <div class="flex items-center gap-2 text-xs text-ink-secondary">
        <Pentagon v-if="areaKm2 !== null" aria-hidden="true" class="h-3.5 w-3.5 text-ink-muted" />
        <MapPin v-else aria-hidden="true" class="h-3.5 w-3.5 text-ink-muted" />
        <span>{{ areaKm2 !== null ? 'Selected area' : 'All Regions' }}</span>
        <span v-if="areaKm2 !== null" class="ml-auto font-mono text-ink-muted"
          >{{ areaKm2.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} km²</span
        >
        <BaseHelpGuidePopover
          :class="areaKm2 === null ? 'ml-auto' : ''"
          title="Filtering & Area Selection"
          summary="Narrow detections by region, UTC dates, and satellite sensor."
          :steps="[
            'Click Draw Area on the bottom dock to sketch a custom polygon.',
            'Pick a Start/End date or sensor (MODIS / VIIRS) to update map & metrics.',
            'Export the filtered records anytime with Download CSV.',
          ]"
          side="left"
          align="start"
          aria-label="How area and filter controls work"
        >
          <template #graphic>
            <DashboardGuideDiagram variant="aoi" />
          </template>
        </BaseHelpGuidePopover>
      </div>
      <div class="grid grid-cols-3 gap-2" role="status" aria-label="Filtered fire metrics">
        <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-2.5">
          <p class="mb-1.5 text-[10px] text-ink-muted">Events</p>
          <p class="font-mono text-xl leading-none font-medium tabular-nums text-orange-300">
            {{ eventCount.toLocaleString() }}
          </p>
        </div>
        <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-2.5">
          <p class="mb-1.5 text-[10px] text-ink-muted">Hotspots</p>
          <p class="font-mono text-xl leading-none font-medium tabular-nums text-accent-bright">
            {{ stats.total.toLocaleString() }}
          </p>
        </div>
        <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-2.5">
          <p class="mb-1.5 text-[10px] text-ink-muted">Avg FRP</p>
          <p class="font-mono text-xl leading-none font-medium tabular-nums text-ink-primary">
            {{ stats.avgFrp }}<span class="ml-0.5 text-[10px] font-normal text-ink-muted">MW</span>
          </p>
        </div>
      </div>
      <HotspotFilters />
      <HotspotCsvExport />
    </div>
  </BaseMapPanel>
</template>
