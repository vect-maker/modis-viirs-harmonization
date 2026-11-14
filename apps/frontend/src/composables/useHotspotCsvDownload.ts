import { nextTick, shallowRef } from 'vue'
import { useObjectUrl } from '@vueuse/core'
import type { FireHotspot } from '@/types/hotspot'
import { hotspotsToCsv } from '@/utils/hotspotCsv'

export function useHotspotCsvDownload() {
  const file = shallowRef<Blob>()
  const url = useObjectUrl(file)
  const isPreparing = shallowRef(false)
  const error = shallowRef('')

  async function download(hotspots: readonly FireHotspot[], filename: string) {
    if (!hotspots.length || isPreparing.value) return false
    isPreparing.value = true
    error.value = ''
    try {
      file.value = new Blob(['\uFEFF', hotspotsToCsv(hotspots)], { type: 'text/csv;charset=utf-8' })
      await nextTick()
      if (!url.value) throw new Error('Download URL unavailable')
      const link = document.createElement('a')
      link.href = url.value
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      return true
    } catch {
      error.value = 'Could not prepare the CSV. Please try again.'
      return false
    } finally {
      isPreparing.value = false
    }
  }

  return { download, isPreparing, error }
}
