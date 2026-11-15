<script setup lang="ts" generic="T extends string | number">
import { Check, ChevronDown } from '@lucide/vue'
import {
  SelectContent,
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  SelectPortal,
  SelectRoot,
  SelectTrigger,
  SelectValue,
  SelectViewport,
} from 'reka-ui'

const props = defineProps<{
  options: readonly { value: T; label: string }[]
  label: string
  disabled?: boolean
}>()

const model = defineModel<T>({ required: true })

function updateValue(value: unknown) {
  const match = props.options.find((option) => option.value === value)
  if (match) model.value = match.value
}
</script>

<template>
  <SelectRoot :model-value="model" :disabled="disabled" @update:model-value="updateValue">
    <SelectTrigger
      :aria-label="label"
      class="inline-flex min-h-9 min-w-24 cursor-pointer items-center justify-between gap-2 rounded-lg border border-border-subtle bg-surface-input px-3 text-xs font-medium text-ink-primary tabular-nums transition-colors duration-150 hover:border-border-strong focus-visible:outline-2 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-50"
    >
      <SelectValue />
      <ChevronDown aria-hidden="true" class="h-3.5 w-3.5 text-ink-muted" />
    </SelectTrigger>
    <SelectPortal>
      <SelectContent
        position="popper"
        :side-offset="6"
        class="z-50 max-h-72 min-w-[var(--reka-select-trigger-width)] overflow-hidden rounded-lg border border-border-strong bg-surface-elevated shadow-[0_8px_24px_rgba(0,0,0,0.45)]"
      >
        <SelectViewport class="p-1">
          <SelectItem
            v-for="option in options"
            :key="option.value"
            :value="option.value"
            class="relative flex min-h-8 cursor-pointer items-center rounded-md py-1.5 pr-8 pl-3 text-xs text-ink-secondary tabular-nums outline-none select-none data-[highlighted]:bg-white/[0.06] data-[highlighted]:text-ink-primary data-[state=checked]:text-accent-bright"
          >
            <SelectItemText>{{ option.label }}</SelectItemText>
            <SelectItemIndicator class="absolute right-2.5 inline-flex items-center">
              <Check aria-hidden="true" class="h-3.5 w-3.5" />
            </SelectItemIndicator>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
