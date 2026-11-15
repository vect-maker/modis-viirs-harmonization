import { shallowRef } from 'vue'
import { defineStore } from 'pinia'
import type { GeoJSONPolygon } from 'zod-geojson'
import {
  useClustersApi,
  type ClusterGeoJsonParams,
  type ClusterHotspotItem,
  type FireEventFeatureCollection,
  type FireEventProperties,
} from '@/api'

export type MapViewMode = 'events' | 'hotspots' | 'both'

const EMPTY_COLLECTION: FireEventFeatureCollection = {
  type: 'FeatureCollection',
  features: [],
}

export const useClustersStore = defineStore('clusters', () => {
  const { getClustersGeoJson, queryClustersGeoJson, getClusterDetail } = useClustersApi()

  const fireEvents = shallowRef<FireEventFeatureCollection>(EMPTY_COLLECTION)
  const viewMode = shallowRef<MapViewMode>('events')
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

  function setViewMode(mode: MapViewMode) {
    viewMode.value = mode
  }

  return {
    fireEvents,
    viewMode,
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
  }
})
