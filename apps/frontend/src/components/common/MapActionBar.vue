<script setup lang="ts">
import { Pentagon, LocateFixed, Trash2, Globe2 } from '@lucide/vue'

defineProps<{ hasArea: boolean }>()
const emit = defineEmits<{ draw: []; recenter: []; clear: []; globe: [] }>()
</script>

<template>
  <div class="flex shrink-0 items-center gap-1" role="group" aria-label="Map tools">
    <button
      type="button"
      class="dock-action dock-action-primary"
      aria-label="Draw an area to filter hotspots"
      title="Draw an area"
      @click="emit('draw')"
    >
      <Pentagon aria-hidden="true" class="h-4 w-4" />
      <span class="sm:hidden">Draw</span><span class="hidden sm:inline">Draw Area</span>
    </button>
    <button
      type="button"
      class="dock-action"
      aria-label="Show all Nicaragua hotspots"
      title="Center on Nicaragua"
      @click="emit('recenter')"
    >
      <LocateFixed aria-hidden="true" class="h-4 w-4" />
      <span class="hidden xl:inline">Nicaragua</span>
    </button>
    <button
      type="button"
      class="dock-action"
      aria-label="Show the satellite globe"
      title="View globe"
      @click="emit('globe')"
    >
      <Globe2 aria-hidden="true" class="h-4 w-4" />
      <span class="hidden xl:inline">Globe</span>
    </button>
    <button
      type="button"
      class="dock-action"
      :disabled="!hasArea"
      aria-label="Clear selected area"
      title="Clear selected area"
      @click="emit('clear')"
    >
      <Trash2 aria-hidden="true" class="h-4 w-4" />
      <span class="hidden xl:inline">Clear Area</span>
    </button>
  </div>
</template>

<style scoped>
.dock-action {
  display: inline-flex;
  min-width: 40px;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 7px;
  padding: 8px 10px;
  color: #a3aab0;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
}
.dock-action:hover:not(:disabled) {
  background: #ffffff0a;
  color: #f5f5f5;
}
.dock-action:focus-visible {
  outline: 2px solid #f87171;
  outline-offset: -2px;
}
.dock-action:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.dock-action-primary {
  color: #fecaca;
  background: #ef444412;
  border: 1px solid #ef444430;
}
.dock-action-primary:hover:not(:disabled) {
  background: #ef444424;
  color: white;
}
</style>
