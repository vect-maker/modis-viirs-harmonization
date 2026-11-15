import { computed, shallowRef, watch } from 'vue'
import { defineStore, storeToRefs } from 'pinia'
import { useFiltersStore } from './filters'
import { useHotspotsStore } from './hotspots'

export type ChartMetric = 'raw' | 'harmonized'
export type ChartAreaScope = 'area' | 'all'

export interface ActiveClusterContext {
  fireId: number
  latitude: number
  longitude: number
  startDate: string
  endDate: string
  directionDeg: number
}

export const useChartFiltersStore = defineStore('chartFilters', () => {
  const hotspotsStore = useHotspotsStore()
  const filtersStore = useFiltersStore()
  const { selectedPolygon } = storeToRefs(hotspotsStore)
  const { dateRange, selectedSensor } = storeToRefs(filtersStore)

  const metric = shallowRef<ChartMetric>('raw')
  const areaScope = shallowRef<ChartAreaScope>(selectedPolygon.value ? 'area' : 'all')
  const selectedYear = shallowRef<number>(2025)
  const activeClusterContext = shallowRef<ActiveClusterContext | null>(null)

  const activePolygon = computed(() =>
    areaScope.value === 'area' ? selectedPolygon.value : null,
  )

  watch(selectedPolygon, (polygon) => {
    areaScope.value = polygon ? 'area' : 'all'
  })

  function setMetric(next: ChartMetric) {
    metric.value = next
  }

  function setAreaScope(next: ChartAreaScope) {
    areaScope.value = next
  }

  function setSelectedYear(year: number) {
    selectedYear.value = year
  }

  function setActiveClusterContext(ctx: ActiveClusterContext | null) {
    activeClusterContext.value = ctx
  }

  return {
    metric,
    areaScope,
    selectedYear,
    selectedPolygon,
    activePolygon,
    dateRange,
    selectedSensor,
    activeClusterContext,
    setMetric,
    setAreaScope,
    setSelectedYear,
    setActiveClusterContext,
  }
})
