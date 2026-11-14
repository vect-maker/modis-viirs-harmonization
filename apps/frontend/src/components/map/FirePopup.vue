<script setup lang="ts">
import { SunMedium, Moon } from '@lucide/vue'
import type { FireHotspot } from '@/types/hotspot'

defineProps<{
  hotspot: FireHotspot
}>()

const emit = defineEmits<{
  (e: 'select', hotspot: FireHotspot): void
}>()
</script>

<template>
  <div class="p-3.5 bg-surface-panel text-ink-primary rounded-lg shadow-xl text-xs min-w-[220px] font-sans border border-border-strong">
    <div class="flex items-center justify-between gap-2 pb-2 mb-2 border-b border-border-subtle">
      <span class="px-2 py-0.5 rounded bg-surface-elevated text-ink-secondary border border-border-subtle font-semibold text-[11px] tracking-wide uppercase">
        {{ hotspot.instrument }} ({{ hotspot.satellite }})
      </span>
      <span class="inline-flex items-center gap-1 text-[10px] text-ink-muted font-mono">
        <SunMedium v-if="hotspot.daynight === 'D'" aria-hidden="true" class="h-3.5 w-3.5" />
        <Moon v-else aria-hidden="true" class="h-3.5 w-3.5" />
        {{ hotspot.daynight === 'D' ? 'Day' : 'Night' }}
      </span>
    </div>

    <div class="space-y-1.5 text-ink-secondary">
      <div class="flex justify-between">
        <span class="text-ink-muted">Acquisition:</span>
        <span class="font-mono text-ink-primary">{{ hotspot.acq_datetime }}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-ink-muted">Coordinates:</span>
        <span class="font-mono text-ink-secondary">
          {{ hotspot.latitude.toFixed(4) }}, {{ hotspot.longitude.toFixed(4) }}
        </span>
      </div>
      <div class="flex justify-between">
        <span class="text-ink-muted">Radiative Power (FRP):</span>
        <span class="font-mono font-semibold text-accent-bright">{{ hotspot.frp }} MW</span>
      </div>
      <div class="flex justify-between">
        <span class="text-ink-muted">Brightness Temp:</span>
        <span class="font-mono text-ink-secondary">{{ hotspot.bright_mir }} K</span>
      </div>
      <div class="flex justify-between">
        <span class="text-ink-muted">Confidence:</span>
        <span class="font-mono text-ink-secondary">{{ hotspot.confidence }}% ({{ hotspot.confidence_class }})</span>
      </div>
    </div>

    <button
      type="button"
      class="mt-3 w-full py-1.5 px-2 bg-surface-elevated hover:bg-surface-elevated/80 text-ink-secondary hover:text-ink-primary rounded text-[11px] font-medium transition cursor-pointer border border-border-strong focus-visible:outline-2 focus-visible:outline-focus"
      @click="emit('select', hotspot)"
    >
      Inspect Hotspot Details
    </button>
  </div>
</template>
