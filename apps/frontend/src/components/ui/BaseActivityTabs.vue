<script setup lang="ts">
import { CalendarDays, ChartColumn } from '@lucide/vue'
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from 'reka-ui'

const view = defineModel<'daily' | 'history'>({ required: true })

function updateView(value: unknown) {
  if (value === 'daily' || value === 'history') view.value = value
}

const tabClass =
  'inline-flex items-center gap-2 border-b-2 border-transparent px-3 py-2.5 text-xs text-ink-muted hover:text-ink-primary data-[state=active]:border-accent data-[state=active]:text-accent-bright focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus cursor-pointer'
</script>

<template>
  <TabsRoot :model-value="view" @update:model-value="updateView">
    <TabsList
      aria-label="Activity views"
      class="flex gap-1 border-b border-border-subtle px-3 pt-2 sm:px-5"
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
      class="focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus"
    >
      <slot name="daily" />
    </TabsContent>
    <TabsContent
      value="history"
      class="focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus"
    >
      <slot name="history" />
    </TabsContent>
  </TabsRoot>
</template>
