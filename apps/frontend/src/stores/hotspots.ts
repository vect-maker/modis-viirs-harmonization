import { computed, shallowRef } from 'vue'
import { defineStore, storeToRefs } from 'pinia'
import {
  useCountriesApi,
  useHotspotsApi,
  usePlatformsApi,
  type CountryResponse,
  type HotspotFiltersRequest,
  type HotspotResponse,
  type PlatformResponse,
} from '@/api'
import { aggregateDailyActivity } from '@/utils/hotspotActivity'
import { useFiltersStore, type SensorFilter } from '@/stores/filters'
import type { DailyHotspotActivity } from '@/types/hotspot'
import type { HotspotDateRange } from '@/types/filters'

export type { SensorFilter }

export const useHotspotsStore = defineStore('hotspots', () => {
  const filters = useFiltersStore()
  const {
    selectedSensor,
    dateRange,
    fetchedDateRange,
    availableDateBounds,
    availableDateSet,
    latestAvailableDate,
  } = storeToRefs(filters)

  const hotspots = shallowRef<HotspotResponse[]>([])
  const aggregatedDailyActivity = shallowRef<DailyHotspotActivity[] | null>(null)
  const platformsById = shallowRef<Map<string, PlatformResponse>>(new Map())
  const countriesById = shallowRef<Map<string, CountryResponse>>(new Map())
  const isLoading = shallowRef(false)
  const loadingProgress = shallowRef<{ loaded: number; total: number } | null>(null)
  const error = shallowRef<string | null>(null)
  const areaHotspots = shallowRef<HotspotResponse[] | null>(null)

  const { getHotspots, getDailyActivity } = useHotspotsApi()
  const { getPlatforms } = usePlatformsApi()
  const { getCountries } = useCountriesApi()

  const hotspotDateSpan = computed<HotspotDateRange | null>(() => {
    const dates = hotspots.value.map((hotspot) => hotspot.acq_datetime.slice(0, 10)).sort()
    const start = dates[0]
    const end = dates.at(-1)
    return start && end ? { start, end } : null
  })

  const availableDates = computed<HotspotDateRange | null>(
    () => availableDateBounds.value ?? hotspotDateSpan.value,
  )

  function getPlatform(platformId: string): PlatformResponse | undefined {
    return platformsById.value.get(platformId)
  }

  function getCountry(countryId: string): CountryResponse | undefined {
    return countriesById.value.get(countryId)
  }

  // This context stays independent of date selection so the timeline never loses its other days.
  const contextHotspots = computed(() => {
    const candidates = areaHotspots.value ?? hotspots.value
    return selectedSensor.value === 'ALL'
      ? candidates
      : candidates.filter(
          (hotspot) => getPlatform(hotspot.platform_id)?.instrument === selectedSensor.value,
        )
  })

  const dailyActivity = computed(() => {
    if (!areaHotspots.value && aggregatedDailyActivity.value !== null) {
      return aggregatedDailyActivity.value
    }
    return aggregateDailyActivity(
      contextHotspots.value,
      fetchedDateRange.value ?? hotspotDateSpan.value,
    )
  })

  const filteredHotspots = computed(() =>
    contextHotspots.value.filter((hotspot) => {
      const date = hotspot.acq_datetime.slice(0, 10)
      // Inclusive calendar dates preserve the whole UTC end day.
      return !dateRange.value || (date >= dateRange.value.start && date <= dateRange.value.end)
    }),
  )

  const stats = computed(() => {
    const visible = filteredHotspots.value
    return {
      total: visible.length,
      modis: visible.filter(
        (hotspot) => getPlatform(hotspot.platform_id)?.instrument === 'MODIS',
      ).length,
      viirs: visible.filter(
        (hotspot) => getPlatform(hotspot.platform_id)?.instrument === 'VIIRS',
      ).length,
      avgFrp: visible.length
        ? (visible.reduce((sum, hotspot) => sum + (hotspot.frp ?? 0), 0) / visible.length).toFixed(1)
        : '—',
    }
  })

  function setAreaHotspots(matches: HotspotResponse[] | null) {
    areaHotspots.value = matches
  }

  async function updateStartDate(start: string | null) {
    const next = filters.resolveStartDateRange(start, availableDates.value)
    if (next !== undefined) await selectDateRange(next)
  }

  async function updateEndDate(end: string | null) {
    const next = filters.resolveEndDateRange(end, availableDates.value)
    if (next !== undefined) await selectDateRange(next)
  }

  async function fetchDailyActivity(range?: HotspotDateRange | null) {
    const activeRange = range ?? fetchedDateRange.value ?? hotspotDateSpan.value
    try {
      const res = await getDailyActivity({
        start_date: activeRange?.start,
        end_date: activeRange?.end,
        instrument: selectedSensor.value === 'ALL' ? undefined : selectedSensor.value,
      })
      aggregatedDailyActivity.value = res.days
    } catch {
      aggregatedDailyActivity.value = null
    }
  }

  function setSensor(sensor: SensorFilter) {
    filters.setSensor(sensor)
    if (aggregatedDailyActivity.value !== null) {
      void fetchDailyActivity()
    }
  }

  function clearHotspots() {
    hotspots.value = []
    aggregatedDailyActivity.value = null
    filters.setFetchedDateRange(null)
  }

  async function selectDateRange(range: HotspotDateRange | null) {
    filters.setDateRange(range)
    if (!range) {
      clearHotspots()
      return
    }
    await fetchHotspots({ start_date: range.start, end_date: range.end, limit: 100 })
  }

  async function fetchHotspots(params?: HotspotFiltersRequest) {
    isLoading.value = true
    loadingProgress.value = null
    error.value = null
    try {
      const pageLimit = params?.limit ?? 100
      const [firstPage, platformsRes, countriesRes] = await Promise.all([
        getHotspots({ ...params, limit: pageLimit, offset: params?.offset ?? 0 }),
        getPlatforms({ limit: 100 }),
        getCountries({ limit: 100 }),
      ])
      platformsById.value = new Map(platformsRes.data.map((p) => [p.id, p]))
      countriesById.value = new Map(countriesRes.data.map((c) => [c.id, c]))
      const allItems = [...firstPage.data]

      // When filtering by date range, fetch all remaining pages in concurrent batches.
      if (params?.start_date && firstPage.total > allItems.length) {
        loadingProgress.value = { loaded: allItems.length, total: firstPage.total }
        const remainingOffsets: number[] = []
        for (let offset = pageLimit; offset < firstPage.total; offset += pageLimit) {
          remainingOffsets.push(offset)
        }
        const batchSize = 5
        for (let i = 0; i < remainingOffsets.length; i += batchSize) {
          const batch = remainingOffsets.slice(i, i + batchSize)
          const pages = await Promise.all(
            batch.map((offset) => getHotspots({ ...params, limit: pageLimit, offset })),
          )
          for (const page of pages) {
            allItems.push(...page.data)
          }
          loadingProgress.value = {
            loaded: Math.min(allItems.length, firstPage.total),
            total: firstPage.total,
          }
        }
      }

      hotspots.value = allItems
      const resolvedRange =
        params?.start_date && params?.end_date
          ? { start: params.start_date, end: params.end_date }
          : null
      filters.setFetchedDateRange(resolvedRange)
      await fetchDailyActivity(resolvedRange)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch hotspots'
    } finally {
      isLoading.value = false
      loadingProgress.value = null
    }
  }

  return {
    hotspots,
    platformsById,
    countriesById,
    isLoading,
    loadingProgress,
    error,
    selectedSensor,
    areaHotspots,
    dateRange,
    fetchedDateRange,
    availableDates,
    availableDateSet,
    latestAvailableDate,
    contextHotspots,
    dailyActivity,
    filteredHotspots,
    stats,
    getPlatform,
    getCountry,
    fetchAvailableDates: filters.fetchAvailableDates,
    fetchHotspots,
    clearHotspots,
    selectDateRange,
    updateStartDate,
    updateEndDate,
    setSensor,
    setAreaHotspots,
    setDateRange: filters.setDateRange,
  }
})
