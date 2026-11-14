<script setup lang="ts">
import { ChartColumn, ChevronUp } from '@lucide/vue'
import { CollapsibleRoot, CollapsibleTrigger, CollapsibleContent } from 'reka-ui'

defineProps<{ summary?: string }>()
const open = defineModel<boolean>('open', { required: true })
</script>

<template>
  <CollapsibleRoot
    v-model:open="open"
    class="overflow-hidden rounded-xl border border-white/15 bg-[#141a1e]/95 text-neutral-100 shadow-[0_8px_32px_#0005] backdrop-blur-xl"
  >
    <div class="flex min-h-14 items-center gap-2 p-1.5">
      <div v-if="$slots.tools" class="shrink-0 border-r border-white/10 pr-2">
        <slot name="tools" />
      </div>
      <CollapsibleTrigger
        class="flex min-h-10 min-w-0 flex-1 items-center gap-2 rounded-lg px-2 text-left text-neutral-300 hover:bg-white/5 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-red-400 sm:px-3"
        :class="open && 'bg-white/5 text-white'"
        :aria-label="`${open ? 'Collapse' : 'Expand'} activity timeline`"
      >
        <ChartColumn
          aria-hidden="true"
          class="h-4 w-4 shrink-0"
          :class="open ? 'text-red-400' : 'text-neutral-500'"
        />
        <span class="text-xs font-medium sm:text-sm">Activity</span>
        <span class="ml-auto hidden truncate text-xs text-neutral-500 lg:block">{{ summary }}</span>
        <ChevronUp
          aria-hidden="true"
          class="ml-auto h-3.5 w-3.5 shrink-0 text-neutral-500 lg:ml-2"
          :class="open && 'rotate-180'"
        />
      </CollapsibleTrigger>
    </div>
    <CollapsibleContent
      class="timeline-content overflow-y-auto overscroll-contain border-t border-white/10 bg-[#10161a]/80"
    >
      <slot />
    </CollapsibleContent>
  </CollapsibleRoot>
</template>

<style scoped>
.timeline-content {
  max-height: min(38dvh, 18rem);
}
</style>
