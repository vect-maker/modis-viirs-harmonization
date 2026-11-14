<script setup lang="ts">
import { shallowRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Download } from '@lucide/vue'
import { useHotspotsStore } from '@/stores/hotspots'
import { useHotspotCsvDownload } from '@/composables/useHotspotCsvDownload'
import { hotspotCsvFilename } from '@/utils/hotspotCsv'

const store = useHotspotsStore()
const { filteredHotspots } = storeToRefs(store)
const { download, isPreparing, error } = useHotspotCsvDownload()
const message = shallowRef('')
watch(filteredHotspots, () => {
  message.value = ''
})
async function exportCsv() {
  const rows = filteredHotspots.value
  const filename = hotspotCsvFilename(
    store.dateRange ?? store.availableDates,
    store.selectedSensor,
    store.areaHotspots !== null,
  )
  message.value = ''
  if (await download(rows, filename))
    message.value = `CSV ready: ${rows.length.toLocaleString()} detections.`
}
</script>

<template>
  <div class="space-y-2 border-t border-white/10 pt-4">
    <button
      type="button"
      class="flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-white/15 bg-[#242d33] px-3 text-xs font-medium text-neutral-200 hover:border-neutral-500 hover:text-white focus-visible:outline-2 focus-visible:outline-red-400 disabled:cursor-not-allowed disabled:opacity-40"
      :disabled="!filteredHotspots.length || isPreparing"
      :aria-label="`Download ${filteredHotspots.length.toLocaleString()} filtered hotspots as CSV`"
      @click="exportCsv"
    >
      <Download aria-hidden="true" class="h-4 w-4" />{{
        isPreparing ? 'Preparing CSV…' : 'Download CSV'
      }}
    </button>
    <p role="status" class="text-[11px] text-neutral-400">{{ error || message }}</p>
  </div>
</template>
