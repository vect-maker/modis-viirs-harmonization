<script setup lang="ts">
import { TooltipContent, TooltipPortal, TooltipRoot, TooltipTrigger } from 'reka-ui'

withDefaults(
  defineProps<{
    text: string
    side?: 'top' | 'right' | 'bottom' | 'left'
    sideOffset?: number
  }>(),
  {
    side: 'top',
    sideOffset: 8,
  },
)
</script>

<template>
  <TooltipRoot>
    <TooltipTrigger as-child>
      <slot />
    </TooltipTrigger>
    <TooltipPortal>
      <TooltipContent
        :side="side"
        :side-offset="sideOffset"
        :collision-padding="12"
        class="z-50 rounded-md border border-white/15 bg-[#141a1e]/95 px-2.5 py-1.5 text-xs font-medium text-neutral-100 shadow-lg backdrop-blur-md select-none"
      >
        {{ text }}
      </TooltipContent>
    </TooltipPortal>
  </TooltipRoot>
</template>
