<script setup lang="ts">
import { computed } from 'vue'
import { Flame, MapPin, Moon, SunMedium } from '@lucide/vue'
import type { CountryResponse, HotspotResponse, PlatformResponse } from '@/api'

const props = defineProps<{
  hotspot: HotspotResponse
  platform?: PlatformResponse
  country?: CountryResponse
}>()

const CONFIDENCE_BADGE: Record<string, { label: string; badgeClass: string }> = {
  high: {
    label: 'High',
    badgeClass: 'border-red-400/40 bg-red-500/15 text-red-300',
  },
  nominal: {
    label: 'Nominal',
    badgeClass: 'border-orange-400/40 bg-orange-500/15 text-orange-300',
  },
  low: {
    label: 'Low',
    badgeClass: 'border-yellow-400/40 bg-yellow-500/15 text-yellow-200',
  },
}

const confidenceMeta = computed(() => {
  const key = (props.hotspot.confidence_class ?? '').toLowerCase()
  return (
    CONFIDENCE_BADGE[key] ?? {
      label: 'Unclassified',
      badgeClass: 'border-border-strong bg-surface-elevated text-ink-muted',
    }
  )
})

const formattedCountry = computed(() =>
  props.country ? props.country.name.replace(/_/g, ' ') : null,
)

const formattedAcquiredAt = computed(() => {
  const raw = props.hotspot.acq_datetime.replace('T', ' ')
  return raw.length >= 16 ? `${raw.slice(0, 16)} UTC` : `${raw} UTC`
})

const formattedConfidence = computed(() => {
  if (props.hotspot.confidence !== null && props.hotspot.confidence !== undefined) {
    return `${props.hotspot.confidence}% · ${confidenceMeta.value.label}`
  }
  return confidenceMeta.value.label
})
</script>

<template>
  <div
    class="min-w-[264px] rounded-xl border border-border-strong bg-surface-panel p-3.5 font-sans text-xs text-ink-primary shadow-2xl"
  >
    <div class="mb-3 flex items-center justify-between gap-2 border-b border-border-subtle pb-2.5 pr-6">
      <span
        class="rounded-md border border-border-subtle bg-surface-elevated px-2 py-0.5 text-[11px] font-semibold tracking-wide text-ink-secondary uppercase"
      >
        {{ platform ? `${platform.instrument} (${platform.satellite})` : 'Unknown sensor' }}
      </span>
      <span
        class="inline-flex shrink-0 items-center gap-1 rounded-full border border-border-subtle bg-surface-elevated/70 px-2 py-0.5 font-mono text-[10px] text-ink-secondary"
      >
        <SunMedium v-if="hotspot.daynight === 'D'" aria-hidden="true" class="size-3 text-amber-300" />
        <Moon v-else aria-hidden="true" class="size-3 text-sky-300" />
        {{ hotspot.daynight === 'D' ? 'Day' : 'Night' }}
      </span>
    </div>

    <div class="mb-3 grid grid-cols-2 gap-2">
      <div class="rounded-lg border border-border-subtle bg-surface-elevated/60 px-2.5 py-2">
        <div class="text-[10px] font-medium tracking-wide text-ink-muted uppercase">
          Radiative Power
        </div>
        <div class="mt-0.5 font-mono text-sm font-semibold text-accent-bright tabular-nums">
          {{ hotspot.frp !== null && hotspot.frp !== undefined ? `${hotspot.frp} MW` : '—' }}
        </div>
      </div>

      <div class="rounded-lg border border-border-subtle bg-surface-elevated/60 px-2.5 py-2">
        <div class="text-[10px] font-medium tracking-wide text-ink-muted uppercase">
          Brightness
        </div>
        <div class="mt-0.5 font-mono text-sm font-semibold text-ink-primary tabular-nums">
          {{
            hotspot.bright_mir !== null && hotspot.bright_mir !== undefined
              ? `${hotspot.bright_mir} K`
              : '—'
          }}
        </div>
      </div>
    </div>

    <dl class="space-y-2 text-[11px]">
      <div class="flex items-center justify-between gap-4">
        <dt class="shrink-0 text-ink-muted">Confidence</dt>
        <dd>
          <span
            :class="[
              'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] font-medium',
              confidenceMeta.badgeClass,
            ]"
          >
            <Flame class="size-3" aria-hidden="true" />
            {{ formattedConfidence }}
          </span>
        </dd>
      </div>

      <div v-if="formattedCountry" class="flex items-center justify-between gap-4">
        <dt class="shrink-0 text-ink-muted">Country</dt>
        <dd class="truncate font-medium text-ink-primary">{{ formattedCountry }}</dd>
      </div>

      <div class="flex items-center justify-between gap-4">
        <dt class="shrink-0 text-ink-muted">Acquired</dt>
        <dd class="whitespace-nowrap font-mono text-ink-primary tabular-nums">
          {{ formattedAcquiredAt }}
        </dd>
      </div>

      <div class="flex items-center justify-between gap-4">
        <dt class="inline-flex shrink-0 items-center gap-1 text-ink-muted">
          <MapPin class="size-3" aria-hidden="true" />
          Coords
        </dt>
        <dd class="whitespace-nowrap font-mono text-ink-secondary tabular-nums">
          {{ hotspot.latitude.toFixed(4) }}, {{ hotspot.longitude.toFixed(4) }}
        </dd>
      </div>
    </dl>
  </div>
</template>
