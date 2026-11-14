<script setup lang="ts">
import { ArrowLeft, ChevronDown, SlidersHorizontal } from '@lucide/vue'
import { CollapsibleRoot, CollapsibleTrigger, CollapsibleContent } from 'reka-ui'

defineProps<{ title: string; homeTo?: string }>()
const open = defineModel<boolean>('open', { required: true })
</script>

<template>
  <CollapsibleRoot
    v-model:open="open"
    class="overflow-hidden rounded-xl border border-border-strong bg-surface-panel/95 text-ink-primary shadow-[0_8px_32px_#0004] backdrop-blur-xl"
  >
    <div class="flex min-h-14 items-center">
      <RouterLink
        v-if="homeTo"
        :to="homeTo"
        aria-label="Back to PyroTrace home"
        title="Back to PyroTrace home"
        class="flex min-h-14 items-center justify-center border-r border-border-subtle px-3 text-ink-muted hover:bg-white/5 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-focus"
      >
        <ArrowLeft aria-hidden="true" class="h-4 w-4" />
      </RouterLink>
      <CollapsibleTrigger
        class="flex min-h-14 flex-1 items-center gap-2.5 px-4 py-3 text-left focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-focus"
        :aria-label="`${open ? 'Collapse' : 'Expand'} ${title.toLowerCase()}`"
      >
        <SlidersHorizontal aria-hidden="true" class="h-4 w-4 text-accent" />
        <span class="flex-1 text-sm font-semibold">{{ title }}</span>
        <ChevronDown
          aria-hidden="true"
          class="h-4 w-4 text-ink-muted transition-transform motion-reduce:transition-none"
          :class="open && 'rotate-180'"
        />
      </CollapsibleTrigger>
    </div>
    <CollapsibleContent
      class="map-panel-content overflow-y-auto overscroll-contain border-t border-border-subtle"
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
