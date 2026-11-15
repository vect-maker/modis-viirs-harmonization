<script setup lang="ts">
import { Loader2 } from '@lucide/vue'

withDefaults(
  defineProps<{
    label?: string
    heightClass?: string
  }>(),
  {
    label: 'Loading chart data…',
    heightClass: 'h-[21rem]',
  },
)
</script>

<template>
  <div
    role="status"
    aria-live="polite"
    :class="heightClass"
    class="flex flex-col items-center justify-center gap-2.5 rounded-lg border border-border-subtle bg-white/[0.02] px-4 text-center"
  >
    <Loader2 class="h-5 w-5 text-accent motion-safe:animate-spin" aria-hidden="true" />
    <p class="text-xs font-medium text-ink-secondary">{{ label }}</p>
  </div>
</template>
