<script setup lang="ts">
import { computed } from 'vue'
import { Flame, Layers, Clock, Maximize2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import type { ClusterHotspotItem, FireEventProperties } from '@/api'

const { t } = useI18n()

const props = defineProps<{
  event: FireEventProperties
  hotspots?: ClusterHotspotItem[]
  isInspecting?: boolean
  isLoadingDetail?: boolean
  inspectedCount?: number
  detailError?: string | null
}>()

const emit = defineEmits<{
  (e: 'inspect', event: FireEventProperties): void
}>()

const ACTIVE_WINDOW_MS = 24 * 60 * 60 * 1000

const effectiveStatus = computed(() => {
  const endStr = props.event.datetime_end ?? props.event.datetime_start
  if (endStr) {
    const endMs = Date.parse(endStr.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(endStr) ? endStr : `${endStr}Z`)
    if (!Number.isNaN(endMs) && Date.now() - endMs > ACTIVE_WINDOW_MS) {
      return props.event.hotspot_count <= 1 ? 'ISOLATED' : 'ENDED'
    }
  }
  const raw = (props.event.status ?? '').toUpperCase()
  if (raw === 'ACTIVO') return 'ACTIVE'
  if (raw === 'AISLADO') return 'ISOLATED'
  if (raw === 'FINALIZADO') return 'ENDED'
  return raw || 'ENDED'
})

const statusBadgeClass = computed(() => {
  switch (effectiveStatus.value) {
    case 'ACTIVE':
      return 'border-red-400/40 bg-red-500/15 text-red-300'
    case 'ISOLATED':
      return 'border-amber-400/40 bg-amber-500/15 text-amber-300'
    default:
      return 'border-slate-400/40 bg-slate-500/15 text-slate-300'
  }
})

const statusLabel = computed(() => {
  switch (effectiveStatus.value) {
    case 'ACTIVE':
      return t('map.eventPopup.active')
    case 'ISOLATED':
      return t('map.eventPopup.isolated')
    default:
      return t('map.eventPopup.ended')
  }
})

const formattedWindow = computed(() => {
  if (!props.event.datetime_start) return t('map.eventPopup.unknownWindow')
  const start = props.event.datetime_start.slice(0, 16).replace('T', ' ')
  const end = props.event.datetime_end?.slice(0, 16).replace('T', ' ')
  return end && end !== start ? `${start} → ${end}` : start
})

const maxHotspotFrp = computed(() => {
  const list = props.hotspots ?? []
  return Math.max(1, ...list.map((h) => h.frp ?? 0))
})
</script>

<template>
  <div
    class="w-[290px] rounded-xl border border-neutral-800 bg-neutral-950/95 p-3.5 text-neutral-100 shadow-2xl backdrop-blur-md"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-center gap-2">
        <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-orange-500/20 text-orange-400">
          <Flame :size="16" />
        </span>
        <div>
          <h3 class="text-sm font-semibold leading-tight text-white">
            {{ t('map.eventPopup.title', { id: event.id }) }}
          </h3>
          <p class="text-[11px] text-neutral-400">
            {{
              t('map.eventPopup.detections', {
                total: event.hotspot_count,
                modis: event.modis_count,
                viirs: event.viirs_count,
              })
            }}
          </p>
        </div>
      </div>
      <span
        class="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
        :class="statusBadgeClass"
      >
        {{ statusLabel }}
      </span>
    </div>

    <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
      <div class="rounded-lg border border-neutral-800/80 bg-neutral-900/70 p-2">
        <span class="flex items-center gap-1 text-[10px] text-neutral-400">
          <Maximize2 :size="11" /> {{ t('map.eventPopup.footprint') }}
        </span>
        <span class="mt-0.5 block font-mono text-sm font-semibold text-white">
          {{ event.area_km2.toFixed(2) }} km²
        </span>
      </div>
      <div class="rounded-lg border border-neutral-800/80 bg-neutral-900/70 p-2">
        <span class="flex items-center gap-1 text-[10px] text-neutral-400">
          <Clock :size="11" /> {{ t('map.eventPopup.duration') }}
        </span>
        <span class="mt-0.5 block font-mono text-sm font-semibold text-white">
          {{ event.duration_h.toFixed(1) }} h
        </span>
      </div>
      <div class="rounded-lg border border-neutral-800/80 bg-neutral-900/70 p-2">
        <span class="text-[10px] text-neutral-400">{{ t('map.eventPopup.maxFrp') }}</span>
        <span class="mt-0.5 block font-mono text-sm font-semibold text-orange-300">
          {{ event.max_frp !== null ? `${event.max_frp.toFixed(1)} MW` : '—' }}
        </span>
      </div>
      <div class="rounded-lg border border-neutral-800/80 bg-neutral-900/70 p-2">
        <span class="text-[10px] text-neutral-400">{{ t('map.eventPopup.harmIndex') }}</span>
        <span class="mt-0.5 block font-mono text-sm font-semibold text-emerald-300">
          {{ event.harmonized_weight !== null ? event.harmonized_weight.toFixed(1) : '—' }}
        </span>
      </div>
    </div>

    <p class="mt-2.5 truncate text-[11px] text-neutral-400" :title="formattedWindow">
      {{ t('map.eventPopup.window', { window: formattedWindow }) }}
    </p>

    <button
      type="button"
      class="mt-3 flex w-full cursor-pointer items-center justify-center gap-1.5 rounded-lg border border-orange-500/40 bg-orange-500/15 px-3 py-1.5 text-xs font-medium text-orange-200 transition hover:bg-orange-500/25 disabled:opacity-50"
      :disabled="isLoadingDetail"
      @click="emit('inspect', event)"
    >
      <Layers :size="13" />
      <span v-if="isLoadingDetail">{{ t('map.eventPopup.loadingHotspots') }}</span>
      <span v-else-if="isInspecting">
        {{ t('map.eventPopup.showingHotspots', { count: inspectedCount ?? event.hotspot_count }) }}
      </span>
      <span v-else>{{ t('map.eventPopup.inspectHotspots') }}</span>
    </button>
    <p v-if="detailError" class="mt-1.5 text-[11px] text-red-400">
      {{ detailError }}
    </p>

    <div
      v-if="isInspecting && hotspots && hotspots.length > 0"
      class="mt-2.5 max-h-36 space-y-1 overflow-y-auto rounded-lg border border-neutral-800 bg-neutral-900/80 p-2"
    >
      <div
        v-for="h in hotspots"
        :key="h.id"
        class="flex items-center justify-between gap-2 text-[11px]"
      >
        <span class="font-mono text-neutral-400">
          {{ h.acq_datetime.slice(5, 16).replace('T', ' ') }}
        </span>
        <span
          class="rounded px-1.5 py-0.5 text-[9px] font-semibold"
          :class="
            (h.instrument ?? '').toUpperCase() === 'MODIS'
              ? 'bg-amber-500/20 text-amber-300'
              : 'bg-sky-500/20 text-sky-300'
          "
        >
          {{ h.instrument ?? 'DET' }}
        </span>
        <div class="flex flex-1 items-center gap-1.5">
          <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-neutral-800">
            <div
              class="h-full rounded-full bg-orange-400"
              :style="{ width: `${Math.min(100, ((h.frp ?? 0) / maxHotspotFrp) * 100)}%` }"
            />
          </div>
          <span class="w-11 text-right font-mono text-neutral-200">
            {{ h.frp != null ? `${h.frp.toFixed(1)}` : '—' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
