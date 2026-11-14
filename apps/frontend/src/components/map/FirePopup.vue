<script setup lang="ts">
import type { FireHotspot } from '@/types/hotspot'

defineProps<{
  hotspot: FireHotspot
}>()

const emit = defineEmits<{
  (e: 'select', hotspot: FireHotspot): void
}>()
</script>

<template>
  <div class="p-3.5 bg-neutral-900 text-white rounded-lg shadow-xl text-xs min-w-[220px] font-sans border border-neutral-700">
    <div class="flex items-center justify-between gap-2 pb-2 mb-2 border-b border-neutral-800">
      <span
        :class="[
          'px-2 py-0.5 rounded font-semibold text-[11px] tracking-wide uppercase',
          hotspot.instrument === 'MODIS'
            ? 'bg-red-950 text-red-400 border border-red-800/60'
            : 'bg-amber-950 text-amber-400 border border-amber-800/60'
        ]"
      >
        {{ hotspot.instrument }} ({{ hotspot.satellite }})
      </span>
      <span class="text-[10px] text-neutral-400 font-mono">
        {{ hotspot.daynight === 'D' ? '☀️ Day' : '🌙 Night' }}
      </span>
    </div>

    <div class="space-y-1.5 text-neutral-300">
      <div class="flex justify-between">
        <span class="text-neutral-400">Acquisition:</span>
        <span class="font-mono text-white">{{ hotspot.acq_datetime }}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-neutral-400">Coordinates:</span>
        <span class="font-mono text-neutral-200">
          {{ hotspot.latitude.toFixed(4) }}, {{ hotspot.longitude.toFixed(4) }}
        </span>
      </div>
      <div class="flex justify-between">
        <span class="text-neutral-400">Radiative Power (FRP):</span>
        <span class="font-mono font-semibold text-orange-400">{{ hotspot.frp }} MW</span>
      </div>
      <div class="flex justify-between">
        <span class="text-neutral-400">Brightness Temp:</span>
        <span class="font-mono text-neutral-200">{{ hotspot.bright_mir }} K</span>
      </div>
      <div class="flex justify-between">
        <span class="text-neutral-400">Confidence:</span>
        <span class="font-mono text-neutral-200">{{ hotspot.confidence }}% ({{ hotspot.confidence_class }})</span>
      </div>
    </div>

    <button
      type="button"
      class="mt-3 w-full py-1.5 px-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 hover:text-white rounded text-[11px] font-medium transition cursor-pointer border border-neutral-700"
      @click="emit('select', hotspot)"
    >
      Inspect Hotspot Details
    </button>
  </div>
</template>
