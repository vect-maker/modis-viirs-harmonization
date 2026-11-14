<script setup lang="ts">
import { ref, computed } from 'vue'
import FireMap from '@/components/map/FireMap.vue'
import type { FireHotspot } from '@/types/hotspot'
import rawHotspots from '@/data/sample_hotspots.json'

const selectedHotspot = ref<FireHotspot | null>(null)
const roiData = ref<{ count: number; areaKm2: number | null }>({
  count: rawHotspots.length,
  areaKm2: null,
})

const allHotspots = rawHotspots as FireHotspot[]

const stats = computed(() => {
  const modis = allHotspots.filter((h) => h.instrument === 'MODIS').length
  const viirs = allHotspots.filter((h) => h.instrument === 'VIIRS').length
  const avgFrp = (allHotspots.reduce((acc, h) => acc + h.frp, 0) / allHotspots.length).toFixed(1)

  return {
    total: allHotspots.length,
    modis,
    viirs,
    avgFrp,
  }
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
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
          </svg>
        </div>
        <div>
          <h1 class="text-base font-bold tracking-tight text-white flex items-center gap-2">
            FIRMS Wildfire Harmonizer
            <span class="text-[10px] font-mono uppercase bg-orange-950 text-orange-400 border border-orange-800/60 px-2 py-0.5 rounded-full">
              NASA Space Apps 2026
            </span>
          </h1>
          <p class="text-xs text-neutral-400">
            Harmonized Active Fire Hotspot Explorer & Burning Activity Calendar
          </p>
        </div>
      </div>

      <div class="flex items-center gap-4 text-xs">
        <div class="hidden sm:flex items-center gap-2 text-neutral-400">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Local DuckDB Sample (March–May 2024)</span>
        </div>
        <a
          href="https://github.com/casey/just"
          target="_blank"
          rel="noopener"
          class="px-2.5 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded border border-neutral-700 transition"
        >
          CLI Justfiles
        </a>
      </div>
    </header>

    <!-- Main Dashboard Workspace -->
    <main class="flex-1 p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      <!-- Quick Metric Cards -->
      <section class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-neutral-900/80 border border-neutral-800 p-4 rounded-xl shadow-sm">
          <p class="text-xs text-neutral-400">Total Loaded Hotspots</p>
          <p class="text-2xl font-bold font-mono text-white mt-1">{{ stats.total.toLocaleString() }}</p>
          <p class="text-[11px] text-neutral-500 mt-0.5">Sample slice (Nicaragua)</p>
        </div>

        <div class="bg-neutral-900/80 border border-neutral-800 p-4 rounded-xl shadow-sm">
          <p class="text-xs text-neutral-400 flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-red-500" />
            MODIS Hotspots
          </p>
          <p class="text-2xl font-bold font-mono text-red-400 mt-1">{{ stats.modis.toLocaleString() }}</p>
          <p class="text-[11px] text-neutral-500 mt-0.5">Terra & Aqua (~1 km)</p>
        </div>

        <div class="bg-neutral-900/80 border border-neutral-800 p-4 rounded-xl shadow-sm">
          <p class="text-xs text-neutral-400 flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-amber-500" />
            VIIRS Hotspots
          </p>
          <p class="text-2xl font-bold font-mono text-amber-400 mt-1">{{ stats.viirs.toLocaleString() }}</p>
          <p class="text-[11px] text-neutral-500 mt-0.5">SNPP & NOAA-20 (375m)</p>
        </div>

        <div class="bg-neutral-900/80 border border-neutral-800 p-4 rounded-xl shadow-sm">
          <p class="text-xs text-neutral-400">Average Radiative Power</p>
          <p class="text-2xl font-bold font-mono text-orange-400 mt-1">{{ stats.avgFrp }} <span class="text-sm font-sans text-neutral-400">MW</span></p>
          <p class="text-[11px] text-neutral-500 mt-0.5">Mean FRP fire intensity</p>
        </div>
      </section>

      <!-- Map & Interactive Workspace -->
      <section class="flex-1 flex flex-col gap-3 min-h-[600px]">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold text-neutral-200">High-Resolution Satellite Hotspot Map (Esri)</h2>
            <span class="text-xs text-neutral-400">• Use polygon tool (top left) to draw an Area of Interest</span>
          </div>

          <div v-if="roiData.areaKm2 !== null" class="text-xs text-neutral-300">
            Filtered: <span class="font-bold text-orange-400 font-mono">{{ roiData.count }}</span> / {{ stats.total }}
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
          <div
            :class="[
              'px-2 py-1 rounded font-bold text-xs uppercase',
              selectedHotspot.instrument === 'MODIS' ? 'bg-red-950 text-red-400' : 'bg-amber-950 text-amber-400'
            ]"
          >
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
          class="px-3 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded cursor-pointer transition"
          @click="selectedHotspot = null"
        >
          Dismiss
        </button>
      </section>
    </main>
  </div>
</template>
