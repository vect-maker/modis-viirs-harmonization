<script setup lang="ts">
import { computed } from 'vue'
import { MapPin, Pentagon } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useLocaleFormatters } from '@/i18n'
import { useHotspotsStore } from '@/stores/hotspots'
import { useClustersStore } from '@/stores/clusters'
import BaseMapPanel from '@/components/ui/BaseMapPanel.vue'
import BaseHelpGuidePopover from '@/components/ui/BaseHelpGuidePopover.vue'
import DashboardGuideDiagram from '@/components/common/DashboardGuideDiagram.vue'
import HotspotFilters from './HotspotFilters.vue'
import HotspotCsvExport from './HotspotCsvExport.vue'

const { t } = useI18n()
const { formatInt, formatDecimal } = useLocaleFormatters()
defineProps<{ areaKm2: number | null }>()
const open = defineModel<boolean>('open', { required: true })
const { stats } = storeToRefs(useHotspotsStore())
const { fireEvents } = storeToRefs(useClustersStore())
const eventCount = computed(() => fireEvents.value.features.length)
</script>

<template>
  <BaseMapPanel v-model:open="open" :title="t('dashboard.controls.title')">
    <div class="space-y-3.5 p-3.5">
      <div class="flex items-center gap-2 text-xs text-ink-secondary">
        <Pentagon v-if="areaKm2 !== null" aria-hidden="true" class="h-3.5 w-3.5 text-ink-muted" />
        <MapPin v-else aria-hidden="true" class="h-3.5 w-3.5 text-ink-muted" />
        <span>{{
          areaKm2 !== null ? t('dashboard.controls.selectedArea') : t('dashboard.controls.allRegions')
        }}</span>
        <span v-if="areaKm2 !== null" class="ml-auto font-mono text-ink-muted"
          >{{ formatDecimal(areaKm2) }} km²</span
        >
        <BaseHelpGuidePopover
          :class="areaKm2 === null ? 'ml-auto' : ''"
          :title="t('dashboard.controls.guideTitle')"
          :summary="t('dashboard.controls.guideSummary')"
          :steps="[
            t('dashboard.controls.guideStep1'),
            t('dashboard.controls.guideStep2'),
            t('dashboard.controls.guideStep3'),
          ]"
          side="left"
          align="start"
          :aria-label="t('dashboard.controls.guideAria')"
        >
          <template #graphic>
            <DashboardGuideDiagram variant="aoi" />
          </template>
        </BaseHelpGuidePopover>
      </div>
      <div class="grid grid-cols-3 gap-2" role="status" :aria-label="t('dashboard.controls.metricsAria')">
        <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-2.5">
          <p class="mb-1.5 text-[10px] text-ink-muted">{{ t('dashboard.controls.events') }}</p>
          <p class="font-mono text-xl leading-none font-medium tabular-nums text-orange-300">
            {{ formatInt(eventCount) }}
          </p>
        </div>
        <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-2.5">
          <p class="mb-1.5 text-[10px] text-ink-muted">{{ t('dashboard.controls.hotspots') }}</p>
          <p class="font-mono text-xl leading-none font-medium tabular-nums text-accent-bright">
            {{ formatInt(stats.total) }}
          </p>
        </div>
        <div class="rounded-lg border border-border-subtle bg-white/[0.03] p-2.5">
          <p class="mb-1.5 text-[10px] text-ink-muted">{{ t('dashboard.controls.avgFrp') }}</p>
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
