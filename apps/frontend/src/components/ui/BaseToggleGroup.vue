<script setup lang="ts" generic="T extends string">
import { ToggleGroupItem, ToggleGroupRoot } from 'reka-ui'

const props = defineProps<{
  options: readonly { value: T; label: string }[]
  label: string
}>()

const model = defineModel<T>({ required: true })

function updateValue(value: unknown) {
  // Reka permite deseleccionar en modo single; mantenemos siempre una opción activa.
  const match = props.options.find((option) => option.value === value)
  if (match) model.value = match.value
}
</script>

<template>
  <ToggleGroupRoot
    type="single"
    :model-value="model"
    :aria-label="label"
    class="inline-flex rounded-lg border border-border-subtle bg-surface-input p-1"
    @update:model-value="updateValue"
  >
    <ToggleGroupItem
      v-for="option in options"
      :key="option.value"
      :value="option.value"
      class="min-h-9 cursor-pointer rounded-md px-3 text-xs font-medium whitespace-nowrap text-ink-muted transition-colors duration-150 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus data-[state=on]:bg-surface-elevated data-[state=on]:text-ink-primary"
    >
      {{ option.label }}
    </ToggleGroupItem>
  </ToggleGroupRoot>
</template>
