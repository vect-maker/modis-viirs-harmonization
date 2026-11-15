<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { FilterX } from '@lucide/vue'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseDateRangePicker from '@/components/ui/BaseDateRangePicker.vue'
import BaseSensorFilter from '@/components/ui/BaseSensorFilter.vue'

const store = useHotspotsStore()
const { dateRange, availableDates, availableDateSet, selectedSensor } = storeToRefs(store)
</script>

<template>
  <section class="space-y-4 border-t border-white/10 pt-4" aria-label="Hotspot filters">
    <div class="space-y-2">
      <div class="flex items-center justify-between gap-2">
        <h3 class="text-[11px] font-medium text-neutral-400">Date Range</h3>
        <button
          v-if="dateRange"
          type="button"
          class="inline-flex items-center gap-1 rounded text-xs text-neutral-400 hover:text-white focus-visible:outline-2 focus-visible:outline-red-400"
          @click="void store.selectDateRange(null)"
        >
          <FilterX aria-hidden="true" class="h-3.5 w-3.5" /> Reset
        </button>
      </div>
      <BaseDateRangePicker
        v-if="availableDates"
        :model-value="dateRange"
        :available-dates="availableDates"
        :available-date-set="availableDateSet"
        @update:model-value="void store.selectDateRange($event)"
      />
    </div>
    <div class="space-y-2">
      <h3 class="text-[11px] font-medium text-neutral-400">Sensor</h3>
      <BaseSensorFilter :model-value="selectedSensor" @update:model-value="store.setSensor" />
    </div>
  </section>
</template>
