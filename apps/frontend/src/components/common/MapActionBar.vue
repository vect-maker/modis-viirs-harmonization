<script setup lang="ts">
import { Check, Pentagon, LocateFixed, Trash2, Globe2, X } from '@lucide/vue'
import BaseTooltip from '@/components/ui/BaseTooltip.vue'

defineProps<{ hasArea: boolean; isDrawing?: boolean }>()
const emit = defineEmits<{ draw: []; confirm: []; cancel: []; locate: []; clear: []; globe: [] }>()

const actionClass =
  'inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] px-2.5 py-2 text-xs font-medium whitespace-nowrap text-ink-muted hover:bg-white/[0.04] hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-30 cursor-pointer'
</script>

<template>
  <div class="flex shrink-0 items-center gap-1" role="group" aria-label="Map tools">
    <template v-if="isDrawing">
      <BaseTooltip text="Confirm drawn area">
        <button
          type="button"
          class="inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] border border-emerald-400/40 bg-emerald-500/15 px-2.5 py-2 text-xs font-medium whitespace-nowrap text-emerald-300 hover:bg-emerald-500/25 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus cursor-pointer"
          aria-label="Confirm drawn area"
          @click="emit('confirm')"
        >
          <Check aria-hidden="true" class="h-4 w-4" />
          <span>Confirm</span>
        </button>
      </BaseTooltip>
      <BaseTooltip text="Cancel drawing">
        <button
          type="button"
          class="inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] border border-red-400/40 bg-red-500/10 px-2.5 py-2 text-xs font-medium whitespace-nowrap text-red-300 hover:bg-red-500/20 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus cursor-pointer"
          aria-label="Cancel drawing"
          @click="emit('cancel')"
        >
          <X aria-hidden="true" class="h-4 w-4" />
          <span>Cancel</span>
        </button>
      </BaseTooltip>
    </template>

    <BaseTooltip v-else-if="hasArea" text="Clear selected area">
      <button
        type="button"
        class="inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] border border-accent/35 bg-accent/10 px-2.5 py-2 text-xs font-medium whitespace-nowrap text-accent-bright hover:bg-accent/20 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus cursor-pointer"
        aria-label="Clear selected area"
        @click="emit('clear')"
      >
        <Trash2 aria-hidden="true" class="h-4 w-4" />
        <span class="sm:hidden">Clear</span><span class="hidden sm:inline">Clear Area</span>
      </button>
    </BaseTooltip>

    <BaseTooltip v-else text="Draw an area to filter hotspots">
      <button
        type="button"
        class="inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] border border-accent/35 bg-accent/10 px-2.5 py-2 text-xs font-medium whitespace-nowrap text-accent-bright hover:bg-accent/20 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus cursor-pointer"
        aria-label="Draw an area to filter hotspots"
        @click="emit('draw')"
      >
        <Pentagon aria-hidden="true" class="h-4 w-4" />
        <span class="sm:hidden">Draw</span><span class="hidden sm:inline">Draw Area</span>
      </button>
    </BaseTooltip>

    <BaseTooltip text="Center on my location">
      <button
        type="button"
        :class="actionClass"
        aria-label="Center map on my current location"
        @click="emit('locate')"
      >
        <LocateFixed aria-hidden="true" class="h-4 w-4" />
        <span class="hidden xl:inline">My Location</span>
      </button>
    </BaseTooltip>
    <BaseTooltip text="View satellite globe">
      <button
        type="button"
        :class="actionClass"
        aria-label="Show the satellite globe"
        @click="emit('globe')"
      >
        <Globe2 aria-hidden="true" class="h-4 w-4" />
        <span class="hidden xl:inline">Globe</span>
      </button>
    </BaseTooltip>
  </div>
</template>
