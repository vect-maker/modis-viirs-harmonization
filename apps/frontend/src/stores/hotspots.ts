import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import { parseDate } from '@internationalized/date'
import type { HotspotDateRange } from '@/types/filters'
import sampleHotspots from '@/data/sample_hotspots.json'
import type { FireHotspot } from '@/types/hotspot'

export type SensorFilter = 'ALL' | FireHotspot['instrument']

export const useHotspotsStore = defineStore('hotspots', () => {
  const hotspots = shallowRef<FireHotspot[]>(sampleHotspots as FireHotspot[])
  const selectedSensor = shallowRef<SensorFilter>('ALL')
  const areaHotspots = shallowRef<FireHotspot[] | null>(null)
  const dateRange = shallowRef<HotspotDateRange | null>(null)

  const availableDates = computed<HotspotDateRange | null>(() => {
    const dates = hotspots.value.map((hotspot) => hotspot.acq_datetime.slice(0, 10)).sort()
    const start = dates[0]
    const end = dates.at(-1)
    return start && end ? { start, end } : null
  })

  const filteredHotspots = computed(() => {
    const candidates = areaHotspots.value ?? hotspots.value
    return candidates.filter((hotspot) => {
      const date = hotspot.acq_datetime.slice(0, 10)
      const matchesSensor =
        selectedSensor.value === 'ALL' || hotspot.instrument === selectedSensor.value
      // FIRMS acquisition dates are UTC. Compare calendar dates to include both full days.
      const matchesDate =
        !dateRange.value || (date >= dateRange.value.start && date <= dateRange.value.end)
      return matchesSensor && matchesDate
    })
  })

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

  return {
    hotspots,
    selectedSensor,
    areaHotspots,
    dateRange,
    availableDates,
    filteredHotspots,
    stats,
    setSensor,
    setAreaHotspots,
    setDateRange,
  }
})
