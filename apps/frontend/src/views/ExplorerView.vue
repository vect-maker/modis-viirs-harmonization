<script setup lang="ts">
import { computed, onMounted, shallowRef, watch, useTemplateRef } from 'vue'
import { useMediaQuery, useElementSize } from '@vueuse/core'
import { storeToRefs } from 'pinia'
import FireMap from '@/components/map/FireMap.vue'
import HotspotDetails from '@/components/map/HotspotDetails.vue'
import HotspotControlPanel from '@/components/features/HotspotControlPanel.vue'
import HotspotTimeline from '@/components/features/HotspotTimeline.vue'
import MapActionBar from '@/components/common/MapActionBar.vue'
import type { FireHotspot } from '@/types/hotspot'
import { useHotspotsStore } from '@/stores/hotspots'

const hotspotsStore = useHotspotsStore()
const { filteredHotspots } = storeToRefs(hotspotsStore)

onMounted(() => {
  void hotspotsStore.fetchHotspots({ limit: 100 })
})
const isDesktop = useMediaQuery('(min-width: 768px)')
const panelOpen = shallowRef(isDesktop.value)
const timelineOpen = shallowRef(false)
const timelineElement = useTemplateRef<HTMLDivElement>('timelineElement')
const { height: timelineHeight } = useElementSize(timelineElement)
const mapBottomInset = computed(() => timelineHeight.value + 24)
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
    class="flex h-dvh min-h-0 flex-col overflow-hidden bg-surface-base font-sans text-ink-primary selection:bg-accent selection:text-surface-base"
  >
    <main class="relative min-h-0 flex-1" aria-label="PyroTrace Nicaragua hotspot map">
      <h1 class="sr-only">PyroTrace — Nicaragua Fire Activity</h1>
      <div class="absolute inset-0">
        <FireMap
          :side-panel-open="panelOpen"
          :bottom-inset="mapBottomInset"
          @hotspot-select="selectedHotspot = $event"
          @roi-change="onRoiChange"
        >
          <template #dock="{ drawArea, clearArea, resetView, showGlobe }">
            <div
              ref="timelineElement"
              class="absolute bottom-3 left-3 right-3 z-20 md:bottom-5 md:left-5"
              :class="panelOpen ? 'md:right-[22.5rem]' : 'md:right-5'"
            >
              <HotspotTimeline v-model:open="timelineOpen">
                <template #tools>
                  <MapActionBar
                    :has-area="areaKm2 !== null"
                    @draw="drawArea"
                    @recenter="resetView"
                    @globe="showGlobe"
                    @clear="clearArea"
                  />
                </template>
              </HotspotTimeline>
            </div>
          </template>
        </FireMap>
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
        class="absolute left-3 right-3 z-20 md:left-5 md:right-auto md:w-80"
        :style="{ bottom: `${mapBottomInset + 64}px` }"
        @close="selectedHotspot = null"
      />
    </main>
  </div>
</template>
