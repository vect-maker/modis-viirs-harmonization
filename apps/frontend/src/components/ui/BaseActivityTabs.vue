<script setup lang="ts">
import { CalendarDays, ChartColumn } from '@lucide/vue'
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from 'reka-ui'
const view = defineModel<'daily' | 'history'>({ required: true })
function updateView(value: unknown) {
  if (value === 'daily' || value === 'history') view.value = value
}
</script>

<template>
  <TabsRoot :model-value="view" @update:model-value="updateView">
    <TabsList
      aria-label="Activity views"
      class="flex gap-1 border-b border-white/10 px-3 pt-2 sm:px-5"
    >
      <TabsTrigger value="daily" class="activity-tab"
        ><ChartColumn aria-hidden="true" class="h-3.5 w-3.5" />Daily Activity</TabsTrigger
      >
      <TabsTrigger value="history" class="activity-tab"
        ><CalendarDays aria-hidden="true" class="h-3.5 w-3.5" />Historical Calendar</TabsTrigger
      >
    </TabsList>
    <TabsContent
      value="daily"
      class="focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-red-400"
      ><slot name="daily"
    /></TabsContent>
    <TabsContent
      value="history"
      class="focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-red-400"
      ><slot name="history"
    /></TabsContent>
  </TabsRoot>
</template>

<style scoped>
.activity-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-bottom: 2px solid transparent;
  padding: 10px 12px;
  color: #89949c;
  font-size: 12px;
  cursor: pointer;
}
.activity-tab:hover {
  color: #fff;
}
.activity-tab[data-state='active'] {
  color: #fecaca;
  border-bottom-color: #ef4444;
}
.activity-tab:focus-visible {
  outline: 2px solid #f87171;
  outline-offset: -2px;
}
</style>
