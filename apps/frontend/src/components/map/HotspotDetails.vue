<script setup lang="ts">
import { onKeyStroke } from '@vueuse/core'
import { X, MapPin, Satellite } from '@lucide/vue'
import type { CountryResponse, HotspotResponse, PlatformResponse } from '@/api'

defineProps<{
  hotspot: HotspotResponse
  platform?: PlatformResponse
  country?: CountryResponse
}>()
const emit = defineEmits<{ close: [] }>()

onKeyStroke('Escape', () => emit('close'))
</script>

<template>
  <section
    aria-label="Selected hotspot details"
    class="rounded-xl border border-border-strong bg-surface-panel/95 p-4 text-ink-primary shadow-xl backdrop-blur-md"
  >
    <div class="mb-3 flex items-center justify-between gap-4">
      <h2 class="flex items-center gap-2 text-sm font-semibold">
        <span aria-hidden="true" class="h-2 w-2 rounded-full bg-accent" />Hotspot Details
      </h2>
      <button
        type="button"
        aria-label="Close hotspot details"
        class="rounded p-1 text-ink-muted hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
        @click="emit('close')"
      >
        <X aria-hidden="true" class="h-4 w-4" />
      </button>
    </div>
    <p class="mb-3 text-xs text-ink-muted">{{ hotspot.acq_datetime.replace('T', ' ') }} UTC</p>
    <dl class="mb-3 grid grid-cols-2 gap-3 border-b border-border-subtle pb-3">
      <div>
        <dt class="mb-1 text-xs text-ink-muted">Radiative Power</dt>
        <dd class="font-mono text-sm">{{ hotspot.frp ?? '—' }} MW</dd>
      </div>
      <div>
        <dt class="mb-1 text-xs text-ink-muted">Brightness</dt>
        <dd class="font-mono text-sm">{{ hotspot.bright_mir ?? '—' }} K</dd>
      </div>
    </dl>
    <p class="mb-2 flex items-center gap-2 text-xs text-ink-muted">
      <MapPin aria-hidden="true" class="h-3.5 w-3.5" /><span class="font-mono"
        >{{ hotspot.latitude.toFixed(4) }}, {{ hotspot.longitude.toFixed(4) }}</span
      ><span v-if="country" class="text-ink-secondary">· {{ country.name }}</span>
    </p>
    <p class="flex items-center gap-2 text-xs text-neutral-400">
      <Satellite aria-hidden="true" class="h-3.5 w-3.5" />{{ platform?.instrument ?? 'Unknown' }} ·
      {{ platform?.satellite ?? 'Unknown' }}
    </p>
  </section>
</template>
