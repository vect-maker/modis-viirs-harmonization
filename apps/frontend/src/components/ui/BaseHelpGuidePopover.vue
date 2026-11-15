<script setup lang="ts">
import { CircleHelp } from '@lucide/vue'
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'

withDefaults(
  defineProps<{
    title: string
    summary: string
    steps?: readonly string[]
    side?: 'top' | 'right' | 'bottom' | 'left'
    align?: 'start' | 'center' | 'end'
    ariaLabel?: string
  }>(),
  {
    steps: () => [],
    side: 'left',
    align: 'start',
    ariaLabel: 'How to use this section',
  },
)
</script>

<template>
  <PopoverRoot>
    <PopoverTrigger as-child>
      <button
        type="button"
        :aria-label="ariaLabel"
        :title="ariaLabel"
        class="inline-flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-md border border-border-subtle bg-white/[0.04] text-ink-muted transition-colors hover:border-border-strong hover:bg-white/[0.08] hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        @click.stop
      >
        <CircleHelp class="size-3.5" aria-hidden="true" />
      </button>
    </PopoverTrigger>

    <PopoverPortal>
      <PopoverContent
        :side="side"
        :align="align"
        :side-offset="8"
        :collision-padding="12"
        class="z-50 w-76 rounded-xl border border-border-strong bg-surface-panel/95 p-3.5 text-xs text-ink-primary shadow-2xl backdrop-blur-md"
      >
        <p class="text-[13px] font-semibold text-ink-primary">{{ title }}</p>
        <p class="mt-1 text-[11px] leading-relaxed text-ink-secondary">{{ summary }}</p>

        <div
          v-if="$slots.graphic"
          class="mt-2.5 overflow-hidden rounded-lg border border-border-subtle bg-surface-base/80 p-2"
        >
          <slot name="graphic" />
        </div>

        <ol v-if="steps.length" class="mt-2.5 space-y-1.5 text-[11px] leading-snug text-ink-secondary">
          <li v-for="(step, idx) in steps" :key="idx" class="flex items-start gap-2">
            <span
              class="mt-0.5 inline-flex size-4 shrink-0 items-center justify-center rounded-full bg-accent/15 font-mono text-[10px] font-semibold text-accent-bright"
            >
              {{ idx + 1 }}
            </span>
            <span>{{ step }}</span>
          </li>
        </ol>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
