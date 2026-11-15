import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import { parseDate } from '@internationalized/date'
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
import type { HotspotDateRange } from '@/types/filters'

export type SensorFilter = 'ALL' | 'MODIS' | 'VIIRS'

export const useHotspotsStore = defineStore('hotspots', () => {
  const hotspots = shallowRef<HotspotResponse[]>([])
  const platformsById = shallowRef<Map<string, PlatformResponse>>(new Map())
  const countriesById = shallowRef<Map<string, CountryResponse>>(new Map())
  const isLoading = shallowRef(false)
  const error = shallowRef<string | null>(null)
  const selectedSensor = shallowRef<SensorFilter>('ALL')
  const areaHotspots = shallowRef<HotspotResponse[] | null>(null)
  const dateRange = shallowRef<HotspotDateRange | null>(null)
  const availableDateList = shallowRef<string[]>([])
  const availableDateBounds = shallowRef<HotspotDateRange | null>(null)

  const { getHotspots, getAvailableDates } = useHotspotsApi()
  const { getPlatforms } = usePlatformsApi()
  const { getCountries } = useCountriesApi()

  const availableDateSet = computed(() => new Set(availableDateList.value))
  const latestAvailableDate = computed(() => availableDateBounds.value?.end ?? null)

  const availableDates = computed<HotspotDateRange | null>(() => {
    if (availableDateBounds.value) return availableDateBounds.value
    const dates = hotspots.value.map((hotspot) => hotspot.acq_datetime.slice(0, 10)).sort()
    const start = dates[0]
    const end = dates.at(-1)
    return start && end ? { start, end } : null
  })

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

  const dailyActivity = computed(() =>
    aggregateDailyActivity(contextHotspots.value, availableDates.value),
  )

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

  function setSensor(sensor: SensorFilter) {
    selectedSensor.value = sensor
  }

  function setAreaHotspots(matches: HotspotResponse[] | null) {
    areaHotspots.value = matches
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

  async function selectDateRange(range: HotspotDateRange | null) {
    setDateRange(range)
    await fetchHotspots(
      range
        ? { start_date: range.start, end_date: range.end, limit: 100 }
        : { limit: 100 },
    )
  }

  async function fetchHotspots(params?: HotspotFiltersRequest) {
    isLoading.value = true
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

      // When filtering by date range, fetch up to 5 pages (500 items) for fuller map coverage.
      if (params?.start_date && firstPage.total > allItems.length) {
        const maxPages = 5
        const extraOffsets: number[] = []
        for (let page = 1; page < maxPages; page++) {
          const nextOffset = page * pageLimit
          if (nextOffset >= firstPage.total) break
          extraOffsets.push(nextOffset)
        }
        if (extraOffsets.length > 0) {
          const extraPages = await Promise.all(
            extraOffsets.map((offset) =>
              getHotspots({ ...params, limit: pageLimit, offset }),
            ),
          )
          for (const page of extraPages) {
            allItems.push(...page.data)
          }
        }
      }

      hotspots.value = allItems
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch hotspots'
    } finally {
      isLoading.value = false
    }
  }

  return {
    hotspots,
    platformsById,
    countriesById,
    isLoading,
    error,
    selectedSensor,
    areaHotspots,
    dateRange,
    availableDates,
    availableDateSet,
    latestAvailableDate,
    contextHotspots,
    dailyActivity,
    filteredHotspots,
    stats,
    getPlatform,
    getCountry,
    fetchAvailableDates,
    fetchHotspots,
    selectDateRange,
    setSensor,
    setAreaHotspots,
    setDateRange,
  }
})
