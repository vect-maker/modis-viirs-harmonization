<script setup lang="ts">
import { computed } from 'vue'
import { ToggleGroupRoot, ToggleGroupItem } from 'reka-ui'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const props = defineProps<{ modelValue: 'ALL' | 'MODIS' | 'VIIRS' }>()
const emit = defineEmits<{ 'update:modelValue': [value: 'ALL' | 'MODIS' | 'VIIRS'] }>()
const options = computed(() => [
  { value: 'ALL', label: t('common.all') },
  { value: 'MODIS', label: t('common.modis') },
  { value: 'VIIRS', label: t('common.viirs') },
] as const)

function updateValue(value: unknown) {
  if (value === 'ALL' || value === 'MODIS' || value === 'VIIRS') emit('update:modelValue', value)
  else emit('update:modelValue', props.modelValue)
}
</script>

<template>
  <ToggleGroupRoot
    type="single"
    :model-value="modelValue"
    :aria-label="t('dashboard.filters.sensorAria')"
    class="flex rounded-lg border border-border-subtle bg-surface-input p-1"
    @update:model-value="updateValue"
  >
    <ToggleGroupItem
      v-for="option in options"
      :key="option.value"
      :value="option.value"
      class="min-h-9 flex-1 rounded-md px-3 text-xs font-medium text-ink-muted hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus data-[state=on]:bg-surface-elevated data-[state=on]:text-ink-primary"
      >{{ option.label }}</ToggleGroupItem
    >
  </ToggleGroupRoot>
</template>
