import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import rawArchive from '@/data/historical_monthly.json'
import type { HistoricalArchive, CalendarSensor } from '@/types/calendar'
import { buildCalendarRows, calendarCount } from '@/utils/historicalCalendar'

export const useCalendarStore = defineStore('calendar', () => {
  const archive = shallowRef<HistoricalArchive>(rawArchive as HistoricalArchive)
  const sensor = shallowRef<CalendarSensor>('ALL')
  const selectedPeriod = shallowRef<{ year: number; month: number } | null>(null)
  const rows = computed(() =>
    buildCalendarRows(
      archive.value.months,
      Number(archive.value.firstDetection.slice(0, 4)),
      Number(archive.value.lastDetection.slice(0, 4)),
      sensor.value,
    ),
  )
  const maxCount = computed(() =>
    Math.max(1, ...rows.value.flatMap((row) => row.cells.map((cell) => cell.count ?? 0))),
  )
  const total = computed(() =>
    archive.value.months.reduce((sum, month) => sum + (calendarCount(month, sensor.value) ?? 0), 0),
  )
  const selectedMonth = computed(() =>
    selectedPeriod.value
      ? (archive.value.months.find(
          (month) =>
            month.year === selectedPeriod.value?.year &&
            month.month === selectedPeriod.value?.month,
        ) ?? null)
      : null,
  )
  const selectedCount = computed(() =>
    calendarCount(selectedMonth.value ?? undefined, sensor.value),
  )
  function setSensor(value: CalendarSensor) {
    sensor.value = value
  }
  function selectMonth(year: number, month: number) {
    if (
      !Number.isInteger(year) ||
      !Number.isInteger(month) ||
      month < 1 ||
      month > 12 ||
      !rows.value.some((row) => row.year === year)
    )
      return
    selectedPeriod.value = { year, month }
  }
  return {
    archive,
    sensor,
    selectedPeriod,
    rows,
    maxCount,
    total,
    selectedMonth,
    selectedCount,
    setSensor,
    selectMonth,
  }
})
