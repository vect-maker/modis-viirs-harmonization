<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import { CalendarDays, ChevronLeft, ChevronRight } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { CalendarDate, parseDate } from '@internationalized/date'
import type { DateValue } from 'reka-ui'
import { useLocaleFormatters } from '@/i18n'
import {
  DatePickerCalendar,
  DatePickerCell,
  DatePickerCellTrigger,
  DatePickerContent,
  DatePickerGrid,
  DatePickerGridBody,
  DatePickerGridHead,
  DatePickerGridRow,
  DatePickerHeadCell,
  DatePickerHeader,
  DatePickerHeading,
  DatePickerNext,
  DatePickerPrev,
  DatePickerRoot,
  DatePickerTrigger,
} from 'reka-ui'

const props = defineProps<{
  modelValue: string | null
  minDate: string
  maxDate: string
  availableDateSet?: Set<string>
  label: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const { t } = useI18n()
const { bcp47Locale } = useLocaleFormatters()

const dateFormatter = computed(
  () =>
    new Intl.DateTimeFormat(bcp47Locale.value, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone: 'UTC',
    }),
)

const parsedValue = computed<DateValue | undefined>(() =>
  props.modelValue ? parseDate(props.modelValue) : undefined,
)
const formattedValue = computed(() => {
  const date = parsedValue.value
  if (!date) return ''
  return dateFormatter.value.format(new Date(Date.UTC(date.year, date.month - 1, date.day)))
})
const minValue = computed(() => parseDate(props.minDate))
const maxValue = computed(() => parseDate(props.maxDate))

const view = ref<'day' | 'month' | 'year'>('day')
const placeholder = shallowRef<DateValue>(parsedValue.value ?? maxValue.value)
const yearRangeStart = ref(Math.floor(placeholder.value.year / 12) * 12)

watch(
  () => [props.modelValue, props.maxDate] as const,
  () => {
    placeholder.value = parsedValue.value ?? maxValue.value
  },
)

const monthFormatter = computed(
  () => new Intl.DateTimeFormat(bcp47Locale.value, { month: 'short', timeZone: 'UTC' }),
)
const monthLabels = computed(() =>
  Array.from({ length: 12 }, (_, i) => monthFormatter.value.format(new Date(Date.UTC(2024, i, 1)))),
)

const yearGrid = computed(() =>
  Array.from({ length: 12 }, (_, index) => yearRangeStart.value + index),
)

function clampPlaceholder(year: number, month: number): DateValue {
  const min = minValue.value
  const max = maxValue.value
  const candidate = new CalendarDate(year, month, 1)
  if (candidate.compare(min) < 0) return min
  if (candidate.compare(max) > 0) return max
  return candidate
}

function isMonthDisabled(monthNumber: number): boolean {
  const year = placeholder.value.year
  const min = minValue.value
  const max = maxValue.value
  return (
    year < min.year ||
    (year === min.year && monthNumber < min.month) ||
    year > max.year ||
    (year === max.year && monthNumber > max.month)
  )
}

function isYearDisabled(year: number): boolean {
  return year < minValue.value.year || year > maxValue.value.year
}

function shiftPlaceholderYear(delta: number) {
  placeholder.value = clampPlaceholder(placeholder.value.year + delta, placeholder.value.month)
}

function openMonthPicker() {
  view.value = 'month'
}

function openYearPicker() {
  yearRangeStart.value = Math.floor(placeholder.value.year / 12) * 12
  view.value = 'year'
}

function selectMonth(monthNumber: number) {
  placeholder.value = clampPlaceholder(placeholder.value.year, monthNumber)
  view.value = 'day'
}

function selectYear(year: number) {
  placeholder.value = clampPlaceholder(year, placeholder.value.month)
  view.value = 'month'
}

function onOpenChange(open: boolean) {
  if (open) {
    placeholder.value = parsedValue.value ?? maxValue.value
  }
  view.value = 'day'
}

function isDateUnavailable(date: DateValue): boolean {
  if (!props.availableDateSet || props.availableDateSet.size === 0) return false
  return !props.availableDateSet.has(date.toString())
}

function onUpdate(value: DateValue | undefined) {
  emit('update:modelValue', value ? value.toString() : null)
}
</script>

<template>
  <div class="space-y-1">
    <span class="block text-[11px] font-medium text-ink-muted">{{ label }}</span>
    <DatePickerRoot
      v-model:placeholder="placeholder"
      :model-value="parsedValue"
      :min-value="minValue"
      :max-value="maxValue"
      :is-date-unavailable="isDateUnavailable"
      :locale="bcp47Locale"
      granularity="day"
      @update:model-value="onUpdate"
      @update:open="onOpenChange"
    >
      <DatePickerTrigger
        type="button"
        :aria-label="`${label}: ${formattedValue || t('dashboard.filters.selectDate')}`"
        class="flex min-h-10 w-full items-center justify-between gap-2 rounded-lg border border-border-strong bg-surface-elevated px-3 py-2 text-left text-xs text-ink-primary transition hover:border-accent/50 focus-visible:outline-2 focus-visible:outline-focus"
      >
        <span :class="formattedValue ? 'tabular-nums text-ink-primary' : 'text-ink-muted'">
          {{ formattedValue || t('dashboard.filters.selectDate') }}
        </span>
        <CalendarDays aria-hidden="true" class="h-4 w-4 shrink-0 text-ink-muted" />
      </DatePickerTrigger>

      <DatePickerContent
        align="end"
        :side-offset="8"
        :collision-padding="16"
        class="z-50 w-72 rounded-xl border border-border-strong bg-surface-panel/95 p-4 text-ink-primary shadow-[0_12px_36px_#0006] backdrop-blur-xl"
      >
        <DatePickerCalendar v-if="view === 'day'" v-slot="{ weekDays, grid }">
          <DatePickerHeader class="mb-3 flex items-center justify-between">
            <DatePickerPrev
              type="button"
              :aria-label="t('dashboard.filters.prevMonth')"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-30"
            >
              <ChevronLeft aria-hidden="true" class="h-4 w-4" />
            </DatePickerPrev>
            <button
              type="button"
              class="rounded-md px-2.5 py-1 text-sm font-medium transition hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus"
              @click="openMonthPicker"
            >
              <DatePickerHeading />
            </button>
            <DatePickerNext
              type="button"
              :aria-label="t('dashboard.filters.nextMonth')"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-30"
            >
              <ChevronRight aria-hidden="true" class="h-4 w-4" />
            </DatePickerNext>
          </DatePickerHeader>

          <DatePickerGrid
            v-for="month in grid"
            :key="month.value.toString()"
            class="w-full table-fixed border-collapse select-none"
          >
            <DatePickerGridHead>
              <DatePickerGridRow>
                <DatePickerHeadCell
                  v-for="day in weekDays"
                  :key="day"
                  class="pb-2 text-[11px] font-normal text-ink-muted"
                >
                  {{ day }}
                </DatePickerHeadCell>
              </DatePickerGridRow>
            </DatePickerGridHead>
            <DatePickerGridBody>
              <DatePickerGridRow v-for="(week, index) in month.rows" :key="index">
                <DatePickerCell
                  v-for="day in week"
                  :key="day.toString()"
                  :date="day"
                  class="py-0.5 text-center"
                >
                  <DatePickerCellTrigger
                    :day="day"
                    :month="month.value"
                    class="flex h-8 w-full items-center justify-center rounded-md text-xs outline-offset-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[unavailable]:pointer-events-none data-[unavailable]:opacity-25 data-[outside-view]:text-ink-muted/50 data-[selected]:bg-accent data-[selected]:text-surface-base"
                  />
                </DatePickerCell>
              </DatePickerGridRow>
            </DatePickerGridBody>
          </DatePickerGrid>
        </DatePickerCalendar>

        <div v-else-if="view === 'month'">
          <div class="mb-3 flex items-center justify-between">
            <button
              type="button"
              :aria-label="t('dashboard.filters.prevYear')"
              :disabled="placeholder.year <= minValue.year"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:pointer-events-none disabled:opacity-30"
              @click="shiftPlaceholderYear(-1)"
            >
              <ChevronLeft aria-hidden="true" class="h-4 w-4" />
            </button>
            <button
              type="button"
              class="rounded-md px-2.5 py-1 text-sm font-medium tabular-nums transition hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus"
              @click="openYearPicker"
            >
              {{ placeholder.year }}
            </button>
            <button
              type="button"
              :aria-label="t('dashboard.filters.nextYear')"
              :disabled="placeholder.year >= maxValue.year"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:pointer-events-none disabled:opacity-30"
              @click="shiftPlaceholderYear(1)"
            >
              <ChevronRight aria-hidden="true" class="h-4 w-4" />
            </button>
          </div>
          <div class="grid grid-cols-3 gap-1.5">
            <button
              v-for="(monthName, idx) in monthLabels"
              :key="monthName"
              type="button"
              :disabled="isMonthDisabled(idx + 1)"
              :class="[
                'flex h-9 items-center justify-center rounded-md text-xs transition focus-visible:outline-2 focus-visible:outline-focus disabled:pointer-events-none disabled:opacity-35',
                placeholder.month === idx + 1
                  ? 'bg-accent font-medium text-surface-base'
                  : 'hover:bg-surface-elevated',
              ]"
              @click="selectMonth(idx + 1)"
            >
              {{ monthName }}
            </button>
          </div>
        </div>

        <div v-else>
          <div class="mb-3 flex items-center justify-between">
            <button
              type="button"
              :aria-label="t('dashboard.filters.prev12Years')"
              :disabled="yearRangeStart <= minValue.year"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:pointer-events-none disabled:opacity-30"
              @click="yearRangeStart -= 12"
            >
              <ChevronLeft aria-hidden="true" class="h-4 w-4" />
            </button>
            <span class="px-2.5 py-1 text-sm font-medium tabular-nums">
              {{ yearRangeStart }} – {{ yearRangeStart + 11 }}
            </span>
            <button
              type="button"
              :aria-label="t('dashboard.filters.next12Years')"
              :disabled="yearRangeStart + 11 >= maxValue.year"
              class="rounded p-2 hover:bg-surface-elevated focus-visible:outline-2 focus-visible:outline-focus disabled:pointer-events-none disabled:opacity-30"
              @click="yearRangeStart += 12"
            >
              <ChevronRight aria-hidden="true" class="h-4 w-4" />
            </button>
          </div>
          <div class="grid grid-cols-3 gap-1.5">
            <button
              v-for="year in yearGrid"
              :key="year"
              type="button"
              :disabled="isYearDisabled(year)"
              :class="[
                'flex h-9 items-center justify-center rounded-md text-xs tabular-nums transition focus-visible:outline-2 focus-visible:outline-focus disabled:pointer-events-none disabled:opacity-35',
                placeholder.year === year
                  ? 'bg-accent font-medium text-surface-base'
                  : 'hover:bg-surface-elevated',
              ]"
              @click="selectYear(year)"
            >
              {{ year }}
            </button>
          </div>
        </div>
      </DatePickerContent>
    </DatePickerRoot>
  </div>
</template>
