<script setup lang="ts">
import { ChevronDown, SlidersHorizontal } from '@lucide/vue'
import { CollapsibleRoot, CollapsibleTrigger, CollapsibleContent } from 'reka-ui'

defineProps<{ title: string }>()
const open = defineModel<boolean>('open', { required: true })
</script>

<template>
  <CollapsibleRoot
    v-model:open="open"
    class="overflow-hidden rounded-xl border border-white/15 bg-[#141a1e]/95 text-neutral-100 shadow-[0_8px_32px_#0004] backdrop-blur-xl"
  >
    <CollapsibleTrigger
      class="flex min-h-14 w-full items-center gap-2.5 px-4 py-3 text-left focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-red-400"
      :aria-label="`${open ? 'Collapse' : 'Expand'} ${title.toLowerCase()}`"
    >
      <SlidersHorizontal aria-hidden="true" class="h-4 w-4 text-red-400" />
      <span class="flex-1 text-sm font-semibold">{{ title }}</span>
      <ChevronDown
        aria-hidden="true"
        class="h-4 w-4 text-neutral-400 transition-transform motion-reduce:transition-none"
        :class="open && 'rotate-180'"
      />
    </CollapsibleTrigger>
    <CollapsibleContent
      class="map-panel-content overflow-y-auto overscroll-contain border-t border-white/10"
    >
      <slot />
    </CollapsibleContent>
  </CollapsibleRoot>
</template>

<style scoped>
.map-panel-content {
  max-height: min(60dvh, calc(100dvh - 10rem));
}
</style>
