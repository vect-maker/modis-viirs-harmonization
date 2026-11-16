<script setup lang="ts">
import { AlertTriangle, Download, X } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'reka-ui'
import { useLocaleFormatters } from '@/i18n'

const { t } = useI18n()
const { formatInt } = useLocaleFormatters()

defineProps<{
  open: boolean
  total: number
  loaded: number
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <DialogRoot :open="open" @update:open="(val) => !val && emit('cancel')">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs" />
      <DialogContent
        class="fixed left-1/2 top-1/2 z-50 w-[min(26rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border-strong bg-surface-panel/95 p-5 text-ink-primary shadow-[0_8px_32px_#0004] backdrop-blur-xl focus:outline-none"
      >
        <div class="mb-2 flex items-start justify-between gap-3">
          <div class="flex items-center gap-2">
            <AlertTriangle aria-hidden="true" class="h-4 w-4 text-accent" />
            <DialogTitle class="text-sm font-semibold">{{
              t('dashboard.dialogs.largeFetch.title')
            }}</DialogTitle>
          </div>
          <DialogClose
            type="button"
            :aria-label="t('dashboard.dialogs.closeAria')"
            class="rounded p-1 text-ink-muted hover:bg-surface-elevated hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <X aria-hidden="true" class="h-4 w-4" />
          </DialogClose>
        </div>

        <DialogDescription class="mb-4 text-xs leading-relaxed text-ink-muted">
          {{ t('dashboard.dialogs.largeFetch.descriptionBefore') }}
          <span class="font-mono font-semibold text-ink-primary">{{ formatInt(total) }}</span>
          {{ t('dashboard.dialogs.largeFetch.descriptionAfter') }}
        </DialogDescription>

        <div class="flex flex-wrap items-center justify-end gap-2 border-t border-border-subtle pt-3">
          <button
            type="button"
            class="rounded-md px-3 py-2 text-xs font-medium text-ink-muted hover:bg-surface-elevated hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus cursor-pointer"
            @click="emit('cancel')"
          >
            {{ t('dashboard.dialogs.largeFetch.keepFirst', { count: formatInt(loaded) }) }}
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-xs font-semibold text-surface-base hover:bg-accent-bright focus-visible:outline-2 focus-visible:outline-focus cursor-pointer"
            @click="emit('confirm')"
          >
            <Download aria-hidden="true" class="h-3.5 w-3.5" />
            {{ t('dashboard.dialogs.largeFetch.downloadAll', { count: formatInt(total) }) }}
          </button>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
