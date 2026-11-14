<script setup lang="ts">
import { onKeyStroke } from '@vueuse/core'
import { X, MapPin, Satellite } from '@lucide/vue'
import type { FireHotspot } from '@/types/hotspot'

defineProps<{ hotspot: FireHotspot }>()
const emit = defineEmits<{ close: [] }>()

onKeyStroke('Escape', () => emit('close'))
</script>

<template>
  <section
    aria-label="Selected hotspot details"
    class="rounded-xl border border-white/10 bg-neutral-950/95 p-4 text-neutral-100 shadow-xl backdrop-blur-md"
  >
    <div class="mb-3 flex items-center justify-between gap-4">
      <h2 class="flex items-center gap-2 text-sm font-semibold">
        <span aria-hidden="true" class="h-2 w-2 rounded-full bg-red-500" />Hotspot Details
      </h2>
      <button
        type="button"
        aria-label="Close hotspot details"
        class="rounded p-1 text-neutral-400 hover:text-white focus-visible:outline-2 focus-visible:outline-red-400"
        @click="emit('close')"
      >
        <X aria-hidden="true" class="h-4 w-4" />
      </button>
    </div>
    <p class="mb-3 text-xs text-neutral-400">{{ hotspot.acq_datetime }} UTC</p>
    <dl class="mb-3 grid grid-cols-2 gap-3 border-b border-white/10 pb-3">
      <div>
        <dt class="mb-1 text-xs text-neutral-400">Radiative Power</dt>
        <dd class="font-mono text-sm">{{ hotspot.frp }} MW</dd>
      </div>
      <div>
        <dt class="mb-1 text-xs text-neutral-400">Brightness</dt>
        <dd class="font-mono text-sm">{{ hotspot.bright_mir }} K</dd>
      </div>
    </dl>
    <p class="mb-2 flex items-center gap-2 text-xs text-neutral-400">
      <MapPin aria-hidden="true" class="h-3.5 w-3.5" /><span class="font-mono"
        >{{ hotspot.latitude.toFixed(4) }}, {{ hotspot.longitude.toFixed(4) }}</span
      >
    </p>
    <p class="flex items-center gap-2 text-xs text-neutral-400">
      <Satellite aria-hidden="true" class="h-3.5 w-3.5" />{{ hotspot.instrument }} ·
      {{ hotspot.satellite }}
    </p>
  </section>
</template>
