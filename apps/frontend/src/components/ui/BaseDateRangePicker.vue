<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { useMediaQuery } from '@vueuse/core'
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
const wideViewport = useMediaQuery('(min-width: 768px)')
const draft = shallowRef<DateRange>({ start: undefined, end: undefined })
const minDate = computed(() => parseDate(props.availableDates.start))
const maxDate = computed(() => parseDate(props.availableDates.end))
const formatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})
const label = computed(() => {
  if (!props.modelValue) return 'All available dates'
  const start = parseDate(props.modelValue.start).toDate('UTC')
  const end = parseDate(props.modelValue.end).toDate('UTC')
  return formatter.formatRange(start, end)
})

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
      class="flex w-full items-center justify-between gap-3 rounded-lg border border-border-subtle bg-surface-input px-3 py-2.5 text-xs text-ink-primary hover:border-border-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      :aria-label="`Filter by date: ${label}`"
    >
      <CalendarRange aria-hidden="true" class="h-4 w-4 text-ink-muted" />
      <span>{{ label }}</span>
      <ChevronDown aria-hidden="true" class="h-4 w-4 text-ink-muted" />
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        :side="wideViewport ? 'left' : 'bottom'"
        align="center"
        position-strategy="fixed"
        :side-offset="12"
        :collision-padding="12"
        :avoid-collisions="true"
        prioritize-position
        sticky="always"
        aria-label="Choose a date range"
        :style="{
          boxSizing: 'border-box',
          width: '20rem',
          maxWidth: 'calc(100vw - 24px)',
          maxHeight: 'min(28rem, calc(100dvh - 24px))',
          overflowX: 'hidden',
          overflowY: 'auto',
        }"
        class="z-50 overflow-y-auto overscroll-contain rounded-xl border border-border-strong bg-surface-panel p-4 text-ink-primary shadow-2xl"
      >
        <div class="mb-3 flex items-center justify-between gap-3">
          <p class="text-sm font-semibold">Date Range</p>
          <PopoverClose
            type="button"
            aria-label="Close calendar"
            class="rounded px-2 py-1 text-ink-muted hover:bg-surface-elevated hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <X aria-hidden="true" class="h-4 w-4" />
          </PopoverClose>
        </div>
        <p class="mb-3 text-xs text-ink-muted">Select a start and end date (UTC).</p>
        <RangeCalendarRoot
          v-slot="{ grid, weekDays }"
          :model-value="draft"
          :default-placeholder="draft.start ?? minDate"
          :min-value="minDate"
          :max-value="maxDate"
          locale="en-US"
          weekday-format="short"
          initial-focus
          prevent-deselect
          @update:model-value="updateRange"
        >
          <RangeCalendarHeader class="mb-3 flex items-center justify-between">
            <RangeCalendarPrev
              type="button"
              aria-label="Previous month"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-30"
            >
              <ChevronLeft aria-hidden="true" class="h-4 w-4" />
            </RangeCalendarPrev>
            <RangeCalendarHeading class="text-sm font-medium" />
            <RangeCalendarNext
              type="button"
              aria-label="Next month"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-30"
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
                  class="pb-2 text-[11px] font-normal text-ink-muted"
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
                    class="flex h-9 w-full items-center justify-center rounded-md text-sm outline-offset-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[outside-view]:text-ink-muted/50 data-[selected]:bg-accent/20 data-[selected]:text-accent-bright data-[selection-start]:bg-accent data-[selection-start]:text-surface-base data-[selection-end]:bg-accent data-[selection-end]:text-surface-base data-[highlighted]:bg-accent/15"
                  />
                </RangeCalendarCell>
              </RangeCalendarGridRow>
            </RangeCalendarGridBody>
          </RangeCalendarGrid>
        </RangeCalendarRoot>
        <div class="mt-3 border-t border-border-subtle pt-3">
          <button
            type="button"
            class="inline-flex w-full items-center justify-center gap-2 rounded-md px-3 py-2 text-sm text-ink-secondary hover:bg-surface-elevated hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
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
