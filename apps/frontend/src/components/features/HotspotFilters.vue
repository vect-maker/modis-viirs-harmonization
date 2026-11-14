<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { FilterX } from '@lucide/vue'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseDateRangePicker from '@/components/ui/BaseDateRangePicker.vue'

const store = useHotspotsStore()
const { dateRange, availableDates, stats } = storeToRefs(store)
</script>

<template>
  <section
    class="flex flex-col gap-3 rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 sm:flex-row sm:items-center sm:justify-between"
    aria-label="Hotspot filters"
  >
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
      <span class="text-sm font-medium text-neutral-300">Dates</span>
      <BaseDateRangePicker
        v-if="availableDates"
        :model-value="dateRange"
        :available-dates="availableDates"
        @update:model-value="store.setDateRange"
      />
      <button
        v-if="dateRange"
        type="button"
        class="inline-flex items-center gap-1.5 self-start rounded px-2 py-2 text-xs text-neutral-400 hover:text-white focus-visible:outline-2 focus-visible:outline-red-400 sm:self-auto"
        @click="store.setDateRange(null)"
      >
        <FilterX aria-hidden="true" class="h-3.5 w-3.5" />
        Reset Dates
      </button>
    </div>
    <p role="status" class="text-xs text-neutral-400">
      {{ stats.total.toLocaleString() }} hotspots
    </p>
  </section>
</template>
