import { onUnmounted, shallowRef, watch, type WatchSource } from 'vue'

export interface ChartLifecycleOptions<T> {
  fetcher: () => Promise<T>
  watchSources?: WatchSource<unknown>[]
  immediate?: boolean
}

/**
 * Manages the full data lifetime of a smart chart component:
 * loading/error state, stale-request protection on rapid filter changes,
 * and automatic cleanup when the component unmounts.
 */
export function useChartLifecycle<T>(options: ChartLifecycleOptions<T>) {
  const data = shallowRef<T | null>(null)
  const isLoading = shallowRef(false)
  const error = shallowRef<string | null>(null)

  let latestRequestId = 0
  let disposed = false

  async function refresh() {
    const requestId = ++latestRequestId
    isLoading.value = true
    error.value = null

    try {
      const result = await options.fetcher()
      if (disposed || requestId !== latestRequestId) return
      data.value = result
    } catch (err) {
      if (disposed || requestId !== latestRequestId) return
      error.value = err instanceof Error ? err.message : 'Unknown error.'
    } finally {
      if (!disposed && requestId === latestRequestId) {
        isLoading.value = false
      }
    }
  }

  if (options.watchSources && options.watchSources.length > 0) {
    watch(options.watchSources, () => {
      void refresh()
    }, { immediate: options.immediate ?? true })
  } else if (options.immediate ?? true) {
    void refresh()
  }

  onUnmounted(() => {
    disposed = true
    latestRequestId++
    data.value = null
  })

  return {
    data,
    isLoading,
    error,
    refresh,
  }
}
