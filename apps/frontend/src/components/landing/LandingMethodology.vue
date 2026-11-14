<script setup lang="ts">
import { Database, GitMerge, Map } from '@lucide/vue'

const stages = [
  {
    step: '01',
    icon: Database,
    title: 'Multi-Sensor Ingestion & Fusion',
    body: 'Quota-aware async fetching pulls NASA FIRMS MODIS, VIIRS SNPP, and NOAA-20/21 archives into ZSTD Parquet and a deterministic UUIDv5 Star Schema for PostGIS.',
    stack: 'Python · DuckDB · PostGIS',
  },
  {
    step: '02',
    icon: GitMerge,
    title: 'Spatio-Temporal Harmonization',
    body: 'Detections are binned into ~2 km hourly quadrants to classify five diurnal/sensitivity regimes and compute VIIRS-equivalent weights without discarding native FRP.',
    stack: 'DuckDB Spatial · 5-Class Model',
  },
  {
    step: '03',
    icon: Map,
    title: 'Interactive Calendar & Explorer',
    body: 'Filter hotspots by custom polygon ROI, date range, and sensor; inspect the 2000–2025 burning activity matrix; and export filtered subsets as RFC-4180 CSV.',
    stack: 'Vue 3 · MapLibre GL · Turf.js',
  },
] as const
</script>

<template>
  <section id="methodology" class="border-b border-border-subtle py-16 sm:py-20">
    <div class="mx-auto max-w-6xl px-4 sm:px-6">
      <div class="max-w-2xl space-y-3">
        <p class="font-mono text-xs uppercase tracking-wider text-telemetry">Architecture</p>
        <h2 class="text-2xl font-bold tracking-tight text-ink-primary sm:text-3xl">
          From Raw Satellite Archives to Actionable Fire Calendars
        </h2>
        <p class="text-sm leading-relaxed text-ink-secondary sm:text-base">
          PyroTrace preserves point-level coordinates and Fire Radiative Power (FRP) while
          reconciling sensor differences in an open, reproducible pipeline.
        </p>
      </div>

      <div class="mt-10 grid gap-5 md:grid-cols-3">
        <article
          v-for="stage in stages"
          :key="stage.step"
          class="flex flex-col rounded-xl border border-border-subtle bg-surface-panel p-6"
        >
          <div class="mb-4 flex items-center justify-between">
            <span
              class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-telemetry/25 bg-telemetry/10 text-telemetry"
            >
              <component :is="stage.icon" aria-hidden="true" class="h-5 w-5" />
            </span>
            <span class="font-mono text-xs font-semibold text-ink-muted">STAGE {{ stage.step }}</span>
          </div>
          <h3 class="text-base font-semibold text-ink-primary">{{ stage.title }}</h3>
          <p class="mt-2 flex-1 text-sm leading-relaxed text-ink-muted">{{ stage.body }}</p>
          <p class="mt-4 border-t border-border-subtle pt-3 font-mono text-[11px] text-ink-secondary">
            {{ stage.stack }}
          </p>
        </article>
      </div>
    </div>
  </section>
</template>
