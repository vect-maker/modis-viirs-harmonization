<script setup lang="ts">
import { shallowRef, watch } from 'vue'
import { FlameKindling, MapPin } from '@lucide/vue'
import { useMediaQuery } from '@vueuse/core'
import { storeToRefs } from 'pinia'
import FireMap from '@/components/map/FireMap.vue'
import HotspotDetails from '@/components/map/HotspotDetails.vue'
import HotspotControlPanel from '@/components/features/HotspotControlPanel.vue'
import type { FireHotspot } from '@/types/hotspot'
import { useHotspotsStore } from '@/stores/hotspots'

const { filteredHotspots } = storeToRefs(useHotspotsStore())
const isDesktop = useMediaQuery('(min-width: 768px)')
const panelOpen = shallowRef(isDesktop.value)
const selectedHotspot = shallowRef<FireHotspot | null>(null)
const areaKm2 = shallowRef<number | null>(null)

watch(filteredHotspots, () => {
  selectedHotspot.value = null
})
function onRoiChange(payload: { areaKm2: number | null }) {
  areaKm2.value = payload.areaKm2
}
</script>

<template>
  <div
    class="flex h-dvh min-h-0 flex-col overflow-hidden bg-neutral-950 font-sans text-neutral-100 selection:bg-red-600 selection:text-white"
  >
    <header
      class="relative z-20 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-white/10 bg-neutral-950 px-4 sm:px-5"
    >
      <div class="flex min-w-0 items-center gap-2.5">
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-600">
          <FlameKindling aria-hidden="true" class="h-5 w-5 text-white" />
        </div>
        <h1 class="truncate text-sm font-semibold tracking-tight sm:text-base">
          FIRMS <span class="font-normal text-neutral-400">Wildfire Harmonizer</span>
        </h1>
      </div>
      <div class="flex shrink-0 items-center gap-4">
        <span
          class="hidden text-[10px] font-medium uppercase tracking-wider text-neutral-500 lg:inline"
          >NASA Space Apps 2026</span
        >
        <span class="flex items-center gap-1.5 text-xs text-neutral-300"
          ><MapPin aria-hidden="true" class="h-3.5 w-3.5 text-neutral-500" />Nicaragua</span
        >
      </div>
    </header>
    <main class="relative min-h-0 flex-1" aria-label="Nicaragua hotspot map">
      <div class="absolute inset-0">
        <FireMap
          :side-panel-open="panelOpen"
          @hotspot-select="selectedHotspot = $event"
          @roi-change="onRoiChange"
        />
      </div>
      <aside
        class="pointer-events-none absolute right-3 top-3 z-20 w-[min(20rem,calc(100%_-_4.5rem))] md:right-5 md:top-5"
        aria-label="Map filters and results"
      >
        <HotspotControlPanel
          v-model:open="panelOpen"
          :area-km2="areaKm2"
          class="pointer-events-auto"
        />
      </aside>
      <HotspotDetails
        v-if="selectedHotspot"
        :hotspot="selectedHotspot"
        class="absolute bottom-24 left-3 right-3 z-20 md:bottom-14 md:left-5 md:right-auto md:w-80"
        @close="selectedHotspot = null"
      />
    </main>
  </div>
</template>
