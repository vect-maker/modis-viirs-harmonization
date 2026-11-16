import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import type { GeoJSONPolygon } from 'zod-geojson'
import {
  useClustersApi,
  type ClusterGeoJsonParams,
  type ClusterHotspotItem,
  type FireEventFeatureCollection,
  type FireEventProperties,
} from '@/api'

export type MapViewMode = 'events' | 'hotspots' | 'both' | 'none'

const EMPTY_COLLECTION: FireEventFeatureCollection = {
  type: 'FeatureCollection',
  features: [],
}

export const useClustersStore = defineStore('clusters', () => {
  const { getClustersGeoJson, queryClustersGeoJson, getClusterDetail } = useClustersApi()

  const fireEvents = shallowRef<FireEventFeatureCollection>(EMPTY_COLLECTION)
  const viewMode = shallowRef<MapViewMode>('both')
  const selectedCluster = shallowRef<FireEventProperties | null>(null)
  const clusterHotspots = shallowRef<ClusterHotspotItem[]>([])
  const hasFetchedEvents = shallowRef(false)
  const isLoading = shallowRef(false)
  const isLoadingDetail = shallowRef(false)
  const error = shallowRef<string | null>(null)

  async function fetchFireEvents(
    params?: ClusterGeoJsonParams & { aoi?: GeoJSONPolygon | null },
  ) {
    isLoading.value = true
    error.value = null
    try {
      if (params?.aoi) {
        fireEvents.value = await queryClustersGeoJson({
          aoi: params.aoi,
          start_date: params.start_date,
          end_date: params.end_date,
          status: params.status,
          min_hotspots: params.min_hotspots ?? 2,
          limit: params.limit ?? 500,
        })
      } else {
        fireEvents.value = await getClustersGeoJson({
          limit: 500,
          bbox: params?.bbox,
          start_date: params?.start_date,
          end_date: params?.end_date,
          status: params?.status,
          min_hotspots: params?.min_hotspots ?? 2,
        })
      }
      hasFetchedEvents.value = true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load fire events'
      fireEvents.value = EMPTY_COLLECTION
    } finally {
      isLoading.value = false
    }
  }

  function clearFireEvents() {
    fireEvents.value = EMPTY_COLLECTION
    hasFetchedEvents.value = false
    clearSelectedCluster()
  }

  async function selectCluster(props: FireEventProperties) {
    selectedCluster.value = props
    isLoadingDetail.value = true
    error.value = null
    try {
      const detail = await getClusterDetail(props.id)
      clusterHotspots.value = detail.data.hotspots
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load constituent hotspots'
      clusterHotspots.value = []
    } finally {
      isLoadingDetail.value = false
    }
  }

  function clearSelectedCluster() {
    selectedCluster.value = null
    clusterHotspots.value = []
  }

  const showEvents = computed(() => viewMode.value === 'events' || viewMode.value === 'both')
  const showHotspots = computed(() => viewMode.value === 'hotspots' || viewMode.value === 'both')

  function setViewMode(mode: MapViewMode) {
    viewMode.value = mode
  }

  function setLayerVisible(layer: 'events' | 'hotspots', visible: boolean) {
    const nextEvents = layer === 'events' ? visible : showEvents.value
    const nextHotspots = layer === 'hotspots' ? visible : showHotspots.value
    if (nextEvents && nextHotspots) {
      viewMode.value = 'both'
    } else if (nextEvents) {
      viewMode.value = 'events'
    } else if (nextHotspots) {
      viewMode.value = 'hotspots'
    } else {
      viewMode.value = 'none'
    }
  }

  return {
    fireEvents,
    viewMode,
    showEvents,
    showHotspots,
    selectedCluster,
    clusterHotspots,
    hasFetchedEvents,
    isLoading,
    isLoadingDetail,
    error,
    fetchFireEvents,
    clearFireEvents,
    selectCluster,
    clearSelectedCluster,
    setViewMode,
    setLayerVisible,
  }
})
