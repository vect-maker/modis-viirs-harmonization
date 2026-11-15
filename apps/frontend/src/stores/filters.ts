import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import { parseDate } from '@internationalized/date'
import { useHotspotsApi } from '@/api'
import type { HotspotDateRange } from '@/types/filters'

export type SensorFilter = 'ALL' | 'MODIS' | 'VIIRS'

export const useFiltersStore = defineStore('filters', () => {
  const selectedSensor = shallowRef<SensorFilter>('ALL')
  const dateRange = shallowRef<HotspotDateRange | null>(null)
  const fetchedDateRange = shallowRef<HotspotDateRange | null>(null)
  const availableDateList = shallowRef<string[]>([])
  const availableDateBounds = shallowRef<HotspotDateRange | null>(null)
  const error = shallowRef<string | null>(null)

  const { getAvailableDates } = useHotspotsApi()

  const availableDateSet = computed(() => new Set(availableDateList.value))
  const latestAvailableDate = computed(() => availableDateBounds.value?.end ?? null)
  const startDate = computed(() => dateRange.value?.start ?? null)
  const endDate = computed(() => dateRange.value?.end ?? null)

  function setSensor(sensor: SensorFilter) {
    selectedSensor.value = sensor
  }

  function setDateRange(range: HotspotDateRange | null) {
    if (range) {
      try {
        if (parseDate(range.start).compare(parseDate(range.end)) > 0) return
      } catch {
        return
      }
    }
    dateRange.value = range ? { ...range } : null
  }

  function setFetchedDateRange(range: HotspotDateRange | null) {
    fetchedDateRange.value = range ? { ...range } : null
  }

  function resolveStartDateRange(
    start: string | null,
    bounds: HotspotDateRange | null,
  ): HotspotDateRange | null | undefined {
    if (!bounds) return undefined
    if (!start) {
      if (!dateRange.value) return undefined
      return { start: bounds.start, end: dateRange.value.end }
    }
    const end = dateRange.value?.end ?? bounds.end
    return { start, end: end < start ? start : end }
  }

  function resolveEndDateRange(
    end: string | null,
    bounds: HotspotDateRange | null,
  ): HotspotDateRange | null | undefined {
    if (!bounds) return undefined
    if (!end) {
      if (!dateRange.value) return undefined
      return { start: dateRange.value.start, end: bounds.end }
    }
    const start = dateRange.value?.start ?? bounds.start
    return { start: start > end ? end : start, end }
  }

  async function fetchAvailableDates() {
    try {
      const res = await getAvailableDates()
      availableDateList.value = res.dates
      availableDateBounds.value =
        res.min_date && res.max_date ? { start: res.min_date, end: res.max_date } : null
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch available dates'
    }
  }

  return {
    selectedSensor,
    dateRange,
    fetchedDateRange,
    availableDateList,
    availableDateBounds,
    availableDateSet,
    latestAvailableDate,
    startDate,
    endDate,
    error,
    setSensor,
    setDateRange,
    setFetchedDateRange,
    resolveStartDateRange,
    resolveEndDateRange,
    fetchAvailableDates,
  }
})
