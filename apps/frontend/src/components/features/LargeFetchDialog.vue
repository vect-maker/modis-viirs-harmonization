<script setup lang="ts">
import { AlertTriangle, Download, X } from '@lucide/vue'
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'reka-ui'

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
            <DialogTitle class="text-sm font-semibold">Large dataset detected</DialogTitle>
          </div>
          <DialogClose
            type="button"
            aria-label="Close dialog"
            class="rounded p-1 text-ink-muted hover:bg-surface-elevated hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
          >
            <X aria-hidden="true" class="h-4 w-4" />
          </DialogClose>
        </div>

        <DialogDescription class="mb-4 text-xs leading-relaxed text-ink-muted">
          The selected query matches
          <span class="font-mono font-semibold text-ink-primary">{{ total.toLocaleString() }}</span>
          fire detections. Downloading all batches may take a while and use more memory in your
          browser.
        </DialogDescription>

        <div class="flex flex-wrap items-center justify-end gap-2 border-t border-border-subtle pt-3">
          <button
            type="button"
            class="rounded-md px-3 py-2 text-xs font-medium text-ink-muted hover:bg-surface-elevated hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus cursor-pointer"
            @click="emit('cancel')"
          >
            Keep first {{ loaded.toLocaleString() }}
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-xs font-semibold text-surface-base hover:bg-accent-bright focus-visible:outline-2 focus-visible:outline-focus cursor-pointer"
            @click="emit('confirm')"
          >
            <Download aria-hidden="true" class="h-3.5 w-3.5" />
            Download all ({{ total.toLocaleString() }})
          </button>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
