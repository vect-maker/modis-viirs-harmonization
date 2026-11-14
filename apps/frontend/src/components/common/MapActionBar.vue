<script setup lang="ts">
import { Pentagon, LocateFixed, Trash2, Globe2 } from '@lucide/vue'
import BaseTooltip from '@/components/ui/BaseTooltip.vue'

defineProps<{ hasArea: boolean }>()
const emit = defineEmits<{ draw: []; recenter: []; clear: []; globe: [] }>()

const actionClass =
  'inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] px-2.5 py-2 text-xs font-medium whitespace-nowrap text-neutral-400 hover:bg-white/[0.04] hover:text-neutral-100 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-red-400 disabled:cursor-not-allowed disabled:opacity-30 cursor-pointer'
</script>

<template>
  <div class="flex shrink-0 items-center gap-1" role="group" aria-label="Map tools">
    <BaseTooltip text="Draw an area to filter hotspots">
      <button
        type="button"
        class="inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] border border-red-500/20 bg-red-500/[0.07] px-2.5 py-2 text-xs font-medium whitespace-nowrap text-red-200 hover:bg-red-500/[0.14] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-red-400 cursor-pointer"
        aria-label="Draw an area to filter hotspots"
        @click="emit('draw')"
      >
        <Pentagon aria-hidden="true" class="h-4 w-4" />
        <span class="sm:hidden">Draw</span><span class="hidden sm:inline">Draw Area</span>
      </button>
    </BaseTooltip>
    <BaseTooltip text="Center on Nicaragua">
      <button
        type="button"
        :class="actionClass"
        aria-label="Show all Nicaragua hotspots"
        @click="emit('recenter')"
      >
        <LocateFixed aria-hidden="true" class="h-4 w-4" />
        <span class="hidden xl:inline">Nicaragua</span>
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
    <BaseTooltip :text="hasArea ? 'Clear selected area' : 'No area selected'">
      <button
        type="button"
        :class="actionClass"
        :disabled="!hasArea"
        aria-label="Clear selected area"
        @click="emit('clear')"
      >
        <Trash2 aria-hidden="true" class="h-4 w-4" />
        <span class="hidden xl:inline">Clear Area</span>
      </button>
    </BaseTooltip>
  </div>
</template>
