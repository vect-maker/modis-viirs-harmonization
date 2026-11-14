<script setup lang="ts">
import { ChartColumn, ChevronUp } from '@lucide/vue'
import { CollapsibleRoot, CollapsibleTrigger, CollapsibleContent } from 'reka-ui'

defineProps<{ summary?: string; large?: boolean }>()
const open = defineModel<boolean>('open', { required: true })
</script>

<template>
  <CollapsibleRoot
    v-model:open="open"
    class="overflow-hidden rounded-xl border border-border-strong bg-surface-panel/95 text-ink-primary shadow-[0_8px_32px_#0005] backdrop-blur-xl"
  >
    <div class="flex min-h-14 items-center gap-2 p-1.5">
      <div v-if="$slots.tools" class="shrink-0 border-r border-border-subtle pr-2">
        <slot name="tools" />
      </div>
      <CollapsibleTrigger
        class="flex min-h-10 min-w-0 flex-1 items-center gap-2 rounded-lg px-2 text-left text-ink-secondary hover:bg-white/5 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus sm:px-3"
        :class="open && 'bg-white/5 text-ink-primary'"
        :aria-label="`${open ? 'Collapse' : 'Expand'} activity timeline`"
      >
        <ChartColumn
          aria-hidden="true"
          class="h-4 w-4 shrink-0"
          :class="open ? 'text-accent' : 'text-ink-muted'"
        />
        <span class="text-xs font-medium sm:text-sm">Activity</span>
        <span class="ml-auto hidden truncate text-xs text-ink-muted lg:block">{{ summary }}</span>
        <ChevronUp
          aria-hidden="true"
          class="ml-auto h-3.5 w-3.5 shrink-0 text-ink-muted lg:ml-2"
          :class="open && 'rotate-180'"
        />
      </CollapsibleTrigger>
    </div>
    <CollapsibleContent
      :data-large="large || undefined"
      class="timeline-content overflow-y-auto overscroll-contain border-t border-border-subtle bg-surface-input/80"
    >
      <slot />
    </CollapsibleContent>
  </CollapsibleRoot>
</template>

<style scoped>
.timeline-content {
  max-height: min(38dvh, 18rem);
}
.timeline-content[data-large] {
  max-height: min(60dvh, 36rem);
}
</style>
