<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { CalendarDays, ChevronLeft, ChevronRight, X } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { parseDate } from '@internationalized/date'
import { useLocaleFormatters } from '@/i18n'
import type { DateValue } from 'reka-ui'
import {
  CalendarCell,
  CalendarCellTrigger,
  CalendarGrid,
  CalendarGridBody,
  CalendarGridHead,
  CalendarGridRow,
  CalendarHeadCell,
  CalendarHeader,
  CalendarHeading,
  CalendarNext,
  CalendarPrev,
  CalendarRoot,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'reka-ui'
import type { HotspotDateRange } from '@/types/filters'

const props = defineProps<{
  open: boolean
  todayDate: string
  availableDates: HotspotDateRange
  availableDateSet: Set<string>
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  'select-date': [date: string]
}>()

const { t } = useI18n()
const { bcp47Locale } = useLocaleFormatters()
const minDate = computed(() => parseDate(props.availableDates.start))
const maxDate = computed(() => parseDate(props.availableDates.end))
const selectedDate = shallowRef<DateValue | undefined>(undefined)

function isDateUnavailable(date: DateValue): boolean {
  if (props.availableDateSet.size === 0) return false
  return !props.availableDateSet.has(date.toString())
}

function onSelectDate(value: DateValue | undefined) {
  if (!value) return
  selectedDate.value = value
  emit('select-date', value.toString())
  emit('update:open', false)
}

function selectLatest() {
  emit('select-date', props.availableDates.end)
  emit('update:open', false)
}
</script>

<template>
  <DialogRoot :open="open" @update:open="emit('update:open', $event)">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs" />
      <DialogContent
        class="fixed left-1/2 top-1/2 z-50 w-[min(22rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border-strong bg-surface-panel/95 p-5 text-ink-primary shadow-[0_8px_32px_#0004] backdrop-blur-xl focus:outline-none"
      >
        <div class="mb-2 flex items-start justify-between gap-3">
          <div class="flex items-center gap-2">
            <CalendarDays aria-hidden="true" class="h-4 w-4 text-accent" />
            <DialogTitle class="text-sm font-semibold">{{
              t('dashboard.dialogs.datePrompt.title')
            }}</DialogTitle>
          </div>
          <DialogClose
            type="button"
            :aria-label="t('dashboard.dialogs.closeAria')"
            class="rounded p-1 text-ink-muted hover:bg-surface-elevated hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <X aria-hidden="true" class="h-4 w-4" />
          </DialogClose>
        </div>
        <DialogDescription class="mb-4 text-xs text-ink-muted">
          {{ t('dashboard.dialogs.datePrompt.descriptionBefore') }}
          <span class="font-medium text-ink-secondary">{{ todayDate }}</span>
          {{ t('dashboard.dialogs.datePrompt.descriptionAfter') }}
        </DialogDescription>

        <CalendarRoot
          v-slot="{ grid, weekDays }"
          :model-value="selectedDate"
          :default-placeholder="maxDate"
          :min-value="minDate"
          :max-value="maxDate"
          :is-date-unavailable="isDateUnavailable"
          :locale="bcp47Locale"
          weekday-format="short"
          @update:model-value="onSelectDate"
        >
          <CalendarHeader class="mb-3 flex items-center justify-between">
            <CalendarPrev
              type="button"
              :aria-label="t('dashboard.filters.prevMonth')"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-30"
            >
              <ChevronLeft aria-hidden="true" class="h-4 w-4" />
            </CalendarPrev>
            <CalendarHeading class="text-sm font-medium" />
            <CalendarNext
              type="button"
              :aria-label="t('dashboard.filters.nextMonth')"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-30"
            >
              <ChevronRight aria-hidden="true" class="h-4 w-4" />
            </CalendarNext>
          </CalendarHeader>
          <CalendarGrid
            v-for="month in grid"
            :key="month.value.toString()"
            class="w-full table-fixed border-collapse select-none"
          >
            <CalendarGridHead>
              <CalendarGridRow>
                <CalendarHeadCell
                  v-for="day in weekDays"
                  :key="day"
                  class="pb-2 text-[11px] font-normal text-ink-muted"
                >
                  {{ day }}
                </CalendarHeadCell>
              </CalendarGridRow>
            </CalendarGridHead>
            <CalendarGridBody>
              <CalendarGridRow v-for="(week, index) in month.rows" :key="index">
                <CalendarCell
                  v-for="day in week"
                  :key="day.toString()"
                  :date="day"
                  class="py-0.5 text-center"
                >
                  <CalendarCellTrigger
                    :day="day"
                    :month="month.value"
                    class="flex h-9 w-full items-center justify-center rounded-md text-sm outline-offset-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[unavailable]:pointer-events-none data-[unavailable]:opacity-25 data-[outside-view]:text-ink-muted/50 data-[selected]:bg-accent data-[selected]:text-surface-base"
                  />
                </CalendarCell>
              </CalendarGridRow>
            </CalendarGridBody>
          </CalendarGrid>
        </CalendarRoot>

        <div class="mt-4 flex flex-col gap-2 border-t border-border-subtle pt-3">
          <button
            type="button"
            class="inline-flex w-full items-center justify-center rounded-md bg-accent px-3 py-2 text-xs font-semibold text-surface-base hover:bg-accent-bright focus-visible:outline-2 focus-visible:outline-focus"
            @click="selectLatest"
          >
            {{ t('dashboard.dialogs.datePrompt.loadLatest', { date: availableDates.end }) }}
          </button>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
