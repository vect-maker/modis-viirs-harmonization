import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import { parseDate } from '@internationalized/date'
import {
  useHotspotsApi,
  usePlatformsApi,
  type HotspotFiltersRequest,
  type HotspotResponse,
  type PlatformResponse,
} from '@/api'
import { aggregateDailyActivity } from '@/utils/hotspotActivity'
import type { HotspotDateRange } from '@/types/filters'
import type { FireHotspot } from '@/types/hotspot'

export type SensorFilter = 'ALL' | FireHotspot['instrument']

function mapHotspotToFireHotspot(
  item: HotspotResponse,
  platformsById: Map<string, PlatformResponse>,
): FireHotspot {
  const platform = platformsById.get(item.platform_id)
  const instrument: FireHotspot['instrument'] =
    platform?.instrument === 'VIIRS' ? 'VIIRS' : 'MODIS'

  return {
    latitude: item.latitude,
    longitude: item.longitude,
    acq_datetime: item.acq_datetime.replace('T', ' '),
    instrument,
    satellite: platform?.satellite ?? 'Unknown',
    confidence_class: item.confidence_class ?? '',
    confidence: item.confidence ?? 0,
    frp: item.frp ?? 0,
    bright_mir: item.bright_mir ?? 0,
    daynight: item.daynight === 'N' ? 'N' : 'D',
  }
}

export const useHotspotsStore = defineStore('hotspots', () => {
  const hotspots = shallowRef<FireHotspot[]>([])
  const isLoading = shallowRef(false)
  const error = shallowRef<string | null>(null)
  const selectedSensor = shallowRef<SensorFilter>('ALL')
  const areaHotspots = shallowRef<FireHotspot[] | null>(null)
  const dateRange = shallowRef<HotspotDateRange | null>(null)

  const { getHotspots } = useHotspotsApi()
  const { getPlatforms } = usePlatformsApi()

  const availableDates = computed<HotspotDateRange | null>(() => {
    const dates = hotspots.value.map((hotspot) => hotspot.acq_datetime.slice(0, 10)).sort()
    const start = dates[0]
    const end = dates.at(-1)
    return start && end ? { start, end } : null
  })

  // This context stays independent of date selection so the timeline never loses its other days.
  const contextHotspots = computed(() => {
    const candidates = areaHotspots.value ?? hotspots.value
    return selectedSensor.value === 'ALL'
      ? candidates
      : candidates.filter((hotspot) => hotspot.instrument === selectedSensor.value)
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
      modis: visible.filter((hotspot) => hotspot.instrument === 'MODIS').length,
      viirs: visible.filter((hotspot) => hotspot.instrument === 'VIIRS').length,
      avgFrp: visible.length
        ? (visible.reduce((sum, hotspot) => sum + hotspot.frp, 0) / visible.length).toFixed(1)
        : '—',
    }
  })

  function setSensor(sensor: SensorFilter) {
    selectedSensor.value = sensor
  }

  function setAreaHotspots(matches: FireHotspot[] | null) {
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

  async function fetchHotspots(params?: HotspotFiltersRequest) {
    isLoading.value = true
    error.value = null
    try {
      const [hotspotsRes, platformsRes] = await Promise.all([
        getHotspots(params),
        getPlatforms({ limit: 100 }),
      ])
      const platformsById = new Map(platformsRes.data.map((p) => [p.id, p]))
      hotspots.value = hotspotsRes.data.map((item) =>
        mapHotspotToFireHotspot(item, platformsById),
      )
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch hotspots'
    } finally {
      isLoading.value = false
    }
  }

  return {
    hotspots,
    isLoading,
    error,
    selectedSensor,
    areaHotspots,
    dateRange,
    availableDates,
    contextHotspots,
    dailyActivity,
    filteredHotspots,
    stats,
    fetchHotspots,
    setSensor,
    setAreaHotspots,
    setDateRange,
  }
})
