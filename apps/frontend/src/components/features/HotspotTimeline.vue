<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { parseDate } from '@internationalized/date'
import { storeToRefs } from 'pinia'
import { FilterX } from '@lucide/vue'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseTimelinePanel from '@/components/ui/BaseTimelinePanel.vue'
import DailyActivityChart from '@/components/common/DailyActivityChart.vue'
import BaseActivityTabs from '@/components/ui/BaseActivityTabs.vue'
import HistoricalCalendar from './HistoricalCalendar.vue'

const open = defineModel<boolean>('open', { required: true })
const view = shallowRef<'daily' | 'history'>('daily')
const store = useHotspotsStore()
const { dailyActivity, dateRange, contextHotspots, availableDates } = storeToRefs(store)
const summary = computed(
  () =>
    `${contextHotspots.value.length.toLocaleString()} detections · ${dailyActivity.value.length} days`,
)
const formatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})
const periodLabel = computed(() =>
  availableDates.value
    ? formatter.formatRange(
        parseDate(availableDates.value.start).toDate('UTC'),
        parseDate(availableDates.value.end).toDate('UTC'),
      )
    : '',
)
function selectDay(date: string) {
  store.setDateRange({ start: date, end: date })
}
</script>

<template>
  <BaseTimelinePanel
    v-model:open="open"
    :summary="view === 'history' ? 'Nicaragua · national archive' : summary"
    :large="view === 'history'"
  >
    <template #tools><slot name="tools" /></template>
    <BaseActivityTabs v-model="view">
      <template #daily>
        <div class="space-y-3 px-3 py-4 sm:px-5">
          <div
            class="flex flex-wrap items-center justify-between gap-2 pl-12 text-xs text-neutral-400"
          >
            <p v-if="availableDates">{{ periodLabel }} · UTC</p>
            <button
              v-if="dateRange"
              type="button"
              class="inline-flex items-center gap-1 rounded text-xs hover:text-white focus-visible:outline-2 focus-visible:outline-red-400"
              @click="store.setDateRange(null)"
            >
              <FilterX aria-hidden="true" class="h-3.5 w-3.5" />Show All Dates
            </button>
          </div>
          <DailyActivityChart
            :days="dailyActivity"
            :selected-range="dateRange"
            @select="selectDay"
          />
          <p
            v-if="!contextHotspots.length"
            role="status"
            class="text-center text-xs text-neutral-400"
          >
            No detections in the available records for this area and sensor.
          </p>
          <p class="pl-12 text-[10px] leading-relaxed text-neutral-500">
            Counts reflect the available records. Daily coverage may be incomplete.
          </p>
        </div>
      </template>
      <template #history><HistoricalCalendar /></template>
    </BaseActivityTabs>
  </BaseTimelinePanel>
</template>
