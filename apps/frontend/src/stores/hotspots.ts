import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import sampleHotspots from '@/data/sample_hotspots.json'
import type { FireHotspot } from '@/types/hotspot'

export type SensorFilter = 'ALL' | FireHotspot['instrument']

export const useHotspotsStore = defineStore('hotspots', () => {
  const hotspots = shallowRef<FireHotspot[]>(sampleHotspots as FireHotspot[])
  const selectedSensor = shallowRef<SensorFilter>('ALL')
  const areaHotspots = shallowRef<FireHotspot[] | null>(null)

  const filteredHotspots = computed(() => {
    const candidates = areaHotspots.value ?? hotspots.value
    return selectedSensor.value === 'ALL'
      ? candidates
      : candidates.filter((hotspot) => hotspot.instrument === selectedSensor.value)
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

  return { hotspots, selectedSensor, areaHotspots, filteredHotspots, stats, setSensor, setAreaHotspots }
})
