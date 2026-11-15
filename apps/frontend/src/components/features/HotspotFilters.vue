<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { FilterX } from '@lucide/vue'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseDatePicker from '@/components/ui/BaseDatePicker.vue'
import BaseSensorFilter from '@/components/ui/BaseSensorFilter.vue'

const store = useHotspotsStore()
const { dateRange, availableDates, availableDateSet, selectedSensor } = storeToRefs(store)

function updateStartDate(start: string | null) {
  if (!availableDates.value) return
  if (!start) {
    if (!dateRange.value) return
    void store.selectDateRange({
      start: availableDates.value.start,
      end: dateRange.value.end,
    })
    return
  }
  const end = dateRange.value?.end ?? availableDates.value.end
  void store.selectDateRange({
    start,
    end: end < start ? start : end,
  })
}

function updateEndDate(end: string | null) {
  if (!availableDates.value) return
  if (!end) {
    if (!dateRange.value) return
    void store.selectDateRange({
      start: dateRange.value.start,
      end: availableDates.value.end,
    })
    return
  }
  const start = dateRange.value?.start ?? availableDates.value.start
  void store.selectDateRange({
    start: start > end ? end : start,
    end,
  })
}
</script>

<template>
  <section class="space-y-4 border-t border-white/10 pt-4" aria-label="Hotspot filters">
    <div class="space-y-2">
      <div class="flex items-center justify-between gap-2">
        <h3 class="text-[11px] font-medium text-neutral-400">Date Filter</h3>
        <button
          v-if="dateRange"
          type="button"
          class="inline-flex items-center gap-1 rounded text-xs text-neutral-400 hover:text-white focus-visible:outline-2 focus-visible:outline-red-400"
          @click="void store.selectDateRange(null)"
        >
          <FilterX aria-hidden="true" class="h-3.5 w-3.5" /> Reset
        </button>
      </div>
      <div v-if="availableDates" class="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <BaseDatePicker
          label="Start Date"
          :model-value="dateRange?.start ?? null"
          :min-date="availableDates.start"
          :max-date="dateRange?.end ?? availableDates.end"
          :available-date-set="availableDateSet"
          @update:model-value="updateStartDate"
        />
        <BaseDatePicker
          label="End Date"
          :model-value="dateRange?.end ?? null"
          :min-date="dateRange?.start ?? availableDates.start"
          :max-date="availableDates.end"
          :available-date-set="availableDateSet"
          @update:model-value="updateEndDate"
        />
      </div>
    </div>
    <div class="space-y-2">
      <h3 class="text-[11px] font-medium text-neutral-400">Sensor</h3>
      <BaseSensorFilter :model-value="selectedSensor" @update:model-value="store.setSensor" />
    </div>
  </section>
</template>
