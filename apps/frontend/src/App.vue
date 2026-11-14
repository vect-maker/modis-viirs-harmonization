<script setup lang="ts">
import { ref, watch } from 'vue'
import { FlameKindling, X } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import FireMap from '@/components/map/FireMap.vue'
import HotspotFilters from '@/components/features/HotspotFilters.vue'
import type { FireHotspot } from '@/types/hotspot'
import { useHotspotsStore } from '@/stores/hotspots'

const hotspotsStore = useHotspotsStore()
const { stats, filteredHotspots } = storeToRefs(hotspotsStore)

const selectedHotspot = ref<FireHotspot | null>(null)
const roiData = ref<{ count: number; areaKm2: number | null }>({
  count: hotspotsStore.hotspots.length,
  areaKm2: null,
})

watch(filteredHotspots, () => {
  selectedHotspot.value = null
})

function onHotspotSelect(hotspot: FireHotspot) {
  selectedHotspot.value = hotspot
}

function onRoiChange(payload: { count: number; areaKm2: number | null }) {
  roiData.value = {
    count: payload.count,
    areaKm2: payload.areaKm2,
  }
}
</script>

<template>
  <div class="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-orange-500 selection:text-white">
    <!-- Top Navigation Header -->
    <header class="border-b border-neutral-800 bg-neutral-900/60 backdrop-blur-md sticky top-0 z-20 px-6 py-3.5 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-orange-600 via-red-600 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-600/30">
          <FlameKindling aria-hidden="true" class="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 class="text-base font-bold tracking-tight text-white flex items-center gap-2">
            FIRMS Wildfire Harmonizer
            <span class="text-[10px] font-mono uppercase bg-orange-950 text-orange-400 border border-orange-800/60 px-2 py-0.5 rounded-full">
              NASA Space Apps 2026
            </span>
          </h1>
          <p class="text-xs text-neutral-400">
            Explore fire activity by area and date
          </p>
        </div>
      </div>

    </header>

    <!-- Main Dashboard Workspace -->
    <main class="flex-1 p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      <HotspotFilters />

      <!-- Quick Metric Cards -->
      <section class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="bg-neutral-900/80 border border-neutral-800 p-4 rounded-xl shadow-sm">
          <p class="text-xs text-neutral-400">Hotspots</p>
          <p class="text-2xl font-bold font-mono text-red-400 mt-1">{{ stats.total.toLocaleString() }}</p>
        </div>

        <div class="bg-neutral-900/80 border border-neutral-800 p-4 rounded-xl shadow-sm">
          <p class="text-xs text-neutral-400">Average Radiative Power</p>
          <p class="text-2xl font-bold font-mono text-orange-400 mt-1">{{ stats.avgFrp }} <span class="text-sm font-sans text-neutral-400">MW</span></p>
        </div>
      </section>

      <!-- Map & Interactive Workspace -->
      <section class="flex-1 flex flex-col gap-3 min-h-[600px]">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold text-neutral-200">Fire Map</h2>
            <span class="text-xs text-neutral-400">Draw an area to filter detections</span>
          </div>

          <div v-if="roiData.areaKm2 !== null" class="text-xs text-neutral-300">
            Filtered: <span class="font-bold text-orange-400 font-mono">{{ stats.total }}</span> / {{ hotspotsStore.hotspots.length }}
          </div>
        </div>

        <!-- The MapLibre Component -->
        <div class="flex-1 min-h-[580px]">
          <FireMap
            @hotspot-select="onHotspotSelect"
            @roi-change="onRoiChange"
          />
        </div>
      </section>

      <!-- Selected Hotspot Detail Drawer (when clicked) -->
      <section
        v-if="selectedHotspot"
        class="bg-neutral-900 border border-neutral-800 p-4 rounded-xl flex items-center justify-between text-xs animate-in fade-in"
      >
        <div class="flex items-center gap-4">
          <div class="px-2 py-1 rounded bg-neutral-800 text-neutral-300 font-bold text-xs uppercase">
            {{ selectedHotspot.instrument }}
          </div>
          <div>
            <p class="font-semibold text-white">
              Satellite {{ selectedHotspot.satellite }} • {{ selectedHotspot.acq_datetime }}
            </p>
            <p class="text-neutral-400">
              Coordinates: {{ selectedHotspot.latitude.toFixed(4) }}, {{ selectedHotspot.longitude.toFixed(4) }} |
              Radiative Power: <span class="text-orange-400 font-mono">{{ selectedHotspot.frp }} MW</span> |
              Brightness: <span class="font-mono">{{ selectedHotspot.bright_mir }} K</span>
            </p>
          </div>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-3 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded cursor-pointer transition"
          @click="selectedHotspot = null"
        >
          <X aria-hidden="true" class="h-3.5 w-3.5" />
          Dismiss
        </button>
      </section>
    </main>
  </div>
</template>
