<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { CalendarRange, ChevronDown, ChevronLeft, ChevronRight, FilterX, X } from '@lucide/vue'
import { parseDate } from '@internationalized/date'
import type { DateRange } from 'reka-ui'
import {
  PopoverRoot,
  PopoverTrigger,
  PopoverPortal,
  PopoverContent,
  PopoverClose,
  RangeCalendarRoot,
  RangeCalendarHeader,
  RangeCalendarHeading,
  RangeCalendarPrev,
  RangeCalendarNext,
  RangeCalendarGrid,
  RangeCalendarGridHead,
  RangeCalendarGridRow,
  RangeCalendarHeadCell,
  RangeCalendarGridBody,
  RangeCalendarCell,
  RangeCalendarCellTrigger,
} from 'reka-ui'
import type { HotspotDateRange } from '@/types/filters'

const props = defineProps<{
  modelValue: HotspotDateRange | null
  availableDates: HotspotDateRange
}>()
const emit = defineEmits<{
  'update:modelValue': [value: HotspotDateRange | null]
}>()
const open = shallowRef(false)
const draft = shallowRef<DateRange>({ start: undefined, end: undefined })
const minDate = computed(() => parseDate(props.availableDates.start))
const maxDate = computed(() => parseDate(props.availableDates.end))
const formatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})
const label = computed(() =>
  props.modelValue
    ? `${formatDate(props.modelValue.start)} – ${formatDate(props.modelValue.end)}`
    : 'All dates',
)

function formatDate(date: string) {
  return formatter.format(parseDate(date).toDate('UTC'))
}

function onOpenChange(value: boolean) {
  if (value) {
    draft.value = props.modelValue
      ? { start: parseDate(props.modelValue.start), end: parseDate(props.modelValue.end) }
      : { start: undefined, end: undefined }
  }
  open.value = value
}

function updateRange(value: DateRange) {
  draft.value = value
  if (!value.start || !value.end || value.start.compare(value.end) > 0) return
  emit('update:modelValue', { start: value.start.toString(), end: value.end.toString() })
  open.value = false
}

function resetRange() {
  emit('update:modelValue', null)
  open.value = false
}
</script>

<template>
  <PopoverRoot :open="open" @update:open="onOpenChange">
    <PopoverTrigger
      type="button"
      class="flex w-full items-center justify-between gap-3 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2.5 text-sm text-neutral-100 hover:border-neutral-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
      :aria-label="`Filter by date: ${label}`"
    >
      <CalendarRange aria-hidden="true" class="h-4 w-4 text-neutral-400" />
      <span>{{ label }}</span>
      <ChevronDown aria-hidden="true" class="h-4 w-4 text-neutral-500" />
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        align="start"
        :side-offset="8"
        aria-label="Choose a date range"
        class="z-50 w-[min(20rem,calc(100vw-2rem))] rounded-xl border border-neutral-700 bg-neutral-900 p-4 text-neutral-100 shadow-2xl"
      >
        <div class="mb-3 flex items-center justify-between gap-3">
          <p class="text-sm font-semibold">Date Range</p>
          <PopoverClose
            type="button"
            aria-label="Close calendar"
            class="rounded px-2 py-1 text-neutral-400 hover:bg-neutral-800 hover:text-white focus-visible:outline-2 focus-visible:outline-red-400"
          >
            <X aria-hidden="true" class="h-4 w-4" />
          </PopoverClose>
        </div>
        <p class="mb-3 text-xs text-neutral-400">Select a start and end date (UTC).</p>
        <RangeCalendarRoot
          v-slot="{ grid, weekDays }"
          :model-value="draft"
          :default-placeholder="draft.start ?? minDate"
          :min-value="minDate"
          :max-value="maxDate"
          locale="en-US"
          weekday-format="short"
          fixed-weeks
          initial-focus
          prevent-deselect
          @update:model-value="updateRange"
        >
          <RangeCalendarHeader class="mb-3 flex items-center justify-between">
            <RangeCalendarPrev
              type="button"
              aria-label="Previous month"
              class="rounded p-2 hover:bg-neutral-800 focus-visible:outline-2 focus-visible:outline-red-400 disabled:opacity-30"
            >
              <ChevronLeft aria-hidden="true" class="h-4 w-4" />
            </RangeCalendarPrev>
            <RangeCalendarHeading class="text-sm font-medium" />
            <RangeCalendarNext
              type="button"
              aria-label="Next month"
              class="rounded p-2 hover:bg-neutral-800 focus-visible:outline-2 focus-visible:outline-red-400 disabled:opacity-30"
            >
              <ChevronRight aria-hidden="true" class="h-4 w-4" />
            </RangeCalendarNext>
          </RangeCalendarHeader>
          <RangeCalendarGrid
            v-for="month in grid"
            :key="month.value.toString()"
            class="w-full table-fixed border-collapse select-none"
          >
            <RangeCalendarGridHead>
              <RangeCalendarGridRow>
                <RangeCalendarHeadCell
                  v-for="day in weekDays"
                  :key="day"
                  class="pb-2 text-[11px] font-normal text-neutral-500"
                  >{{ day }}</RangeCalendarHeadCell
                >
              </RangeCalendarGridRow>
            </RangeCalendarGridHead>
            <RangeCalendarGridBody>
              <RangeCalendarGridRow v-for="(week, index) in month.rows" :key="index">
                <RangeCalendarCell
                  v-for="day in week"
                  :key="day.toString()"
                  :date="day"
                  class="py-0.5 text-center"
                >
                  <RangeCalendarCellTrigger
                    :day="day"
                    :month="month.value"
                    class="flex h-9 w-full items-center justify-center rounded-md text-sm outline-offset-2 hover:bg-neutral-700 focus-visible:outline-2 focus-visible:outline-red-400 data-[disabled]:pointer-events-none data-[disabled]:opacity-25 data-[outside-view]:text-neutral-600 data-[selected]:bg-red-500/20 data-[selected]:text-red-100 data-[selection-start]:bg-red-600 data-[selection-end]:bg-red-600 data-[highlighted]:bg-red-500/15"
                  />
                </RangeCalendarCell>
              </RangeCalendarGridRow>
            </RangeCalendarGridBody>
          </RangeCalendarGrid>
        </RangeCalendarRoot>
        <div class="mt-3 border-t border-neutral-800 pt-3">
          <button
            type="button"
            class="inline-flex w-full items-center justify-center gap-2 rounded-md px-3 py-2 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-white focus-visible:outline-2 focus-visible:outline-red-400"
            @click="resetRange"
          >
            <FilterX aria-hidden="true" class="h-3.5 w-3.5" />
            Show All Dates
          </button>
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
