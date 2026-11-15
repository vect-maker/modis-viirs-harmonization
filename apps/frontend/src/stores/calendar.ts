import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import { useHotspotsApi } from '@/api'
import type { HistoricalArchive, CalendarSensor } from '@/types/calendar'
import { buildCalendarRows, calendarCount } from '@/utils/historicalCalendar'

const EMPTY_ARCHIVE: HistoricalArchive = {
  country: 'All Regions',
  timezone: 'UTC',
  harmonized: false,
  coverageVerified: false,
  source: 'Backend API',
  totalRecords: 0,
  firstDetection: '',
  lastDetection: '',
  months: [],
}

export const useCalendarStore = defineStore('calendar', () => {
  const archive = shallowRef<HistoricalArchive>(EMPTY_ARCHIVE)
  const isLoading = shallowRef(false)
  const hasLoaded = shallowRef(false)
  const error = shallowRef<string | null>(null)
  const sensor = shallowRef<CalendarSensor>('ALL')
  const selectedPeriod = shallowRef<{ year: number; month: number } | null>(null)

  const { getHistoricalCalendar } = useHotspotsApi()

  const rows = computed(() =>
    archive.value.firstDetection && archive.value.lastDetection
      ? buildCalendarRows(
          archive.value.months,
          Number(archive.value.firstDetection.slice(0, 4)),
          Number(archive.value.lastDetection.slice(0, 4)),
          sensor.value,
        )
      : [],
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

  async function fetchHistoricalCalendar() {
    if (hasLoaded.value || isLoading.value) return
    isLoading.value = true
    error.value = null
    try {
      const res = await getHistoricalCalendar()
      if (res.first_detection && res.last_detection) {
        archive.value = {
          ...archive.value,
          totalRecords: res.total_records,
          firstDetection: res.first_detection,
          lastDetection: res.last_detection,
          months: res.months.map((m) => ({
            year: m.year,
            month: m.month,
            total: m.total,
            modisCount: m.modis_count,
            viirsCount: m.viirs_count,
            observedDays: m.observed_days,
            avgFrp: 0,
            firstDetection: '',
            lastDetection: '',
          })),
        }
      }
      hasLoaded.value = true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch historical calendar'
    } finally {
      isLoading.value = false
    }
  }

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
    isLoading,
    hasLoaded,
    error,
    sensor,
    selectedPeriod,
    rows,
    maxCount,
    total,
    selectedMonth,
    selectedCount,
    fetchHistoricalCalendar,
    setSensor,
    selectMonth,
  }
})
