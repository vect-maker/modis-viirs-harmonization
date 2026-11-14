<script setup lang="ts">
import { CalendarDays, ChartColumn } from '@lucide/vue'
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from 'reka-ui'

const view = defineModel<'daily' | 'history'>({ required: true })

function updateView(value: unknown) {
  if (value === 'daily' || value === 'history') view.value = value
}

const tabClass =
  'inline-flex items-center gap-2 border-b-2 border-transparent px-3 py-2.5 text-xs text-neutral-400 hover:text-white data-[state=active]:border-red-500 data-[state=active]:text-red-200 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-red-400 cursor-pointer'
</script>

<template>
  <TabsRoot :model-value="view" @update:model-value="updateView">
    <TabsList
      aria-label="Activity views"
      class="flex gap-1 border-b border-white/10 px-3 pt-2 sm:px-5"
    >
      <TabsTrigger value="daily" :class="tabClass">
        <ChartColumn aria-hidden="true" class="h-3.5 w-3.5" />Daily Activity
      </TabsTrigger>
      <TabsTrigger value="history" :class="tabClass">
        <CalendarDays aria-hidden="true" class="h-3.5 w-3.5" />Historical Calendar
      </TabsTrigger>
    </TabsList>
    <TabsContent
      value="daily"
      class="focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-red-400"
    >
      <slot name="daily" />
    </TabsContent>
    <TabsContent
      value="history"
      class="focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-red-400"
    >
      <slot name="history" />
    </TabsContent>
  </TabsRoot>
</template>
