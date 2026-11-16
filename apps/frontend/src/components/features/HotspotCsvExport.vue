<script setup lang="ts">
import { shallowRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Download } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useLocaleFormatters } from '@/i18n'
import { useHotspotsStore } from '@/stores/hotspots'
import { useHotspotCsvDownload } from '@/composables/useHotspotCsvDownload'
import { hotspotCsvFilename } from '@/utils/hotspotCsv'

const { t } = useI18n()
const { formatInt } = useLocaleFormatters()
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
    store.selectedPolygon !== null,
  )
  message.value = ''
  if (await download(rows, filename, store.platformsById, store.countriesById))
    message.value = t('dashboard.csv.ready', { count: formatInt(rows.length) })
}
</script>

<template>
  <div class="space-y-2 border-t border-border-subtle pt-4">
    <button
      type="button"
      class="flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-border-strong bg-surface-elevated px-3 text-xs font-medium text-ink-secondary hover:border-accent/60 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-40"
      :disabled="!filteredHotspots.length || isPreparing"
      :aria-label="t('dashboard.csv.downloadAria', { count: formatInt(filteredHotspots.length) })"
      @click="exportCsv"
    >
      <Download aria-hidden="true" class="h-4 w-4" />{{
        isPreparing ? t('dashboard.csv.preparing') : t('dashboard.csv.download')
      }}
    </button>
    <p role="status" class="text-[11px] text-ink-muted">{{ error || message }}</p>
  </div>
</template>
