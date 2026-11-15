<script setup lang="ts">
import { ArrowRight, FlaskConical, ShieldAlert, Trees } from '@lucide/vue'

const audiences = [
  {
    icon: ShieldAlert,
    title: 'Early-Warning & Civil Protection',
    body: 'Compare current fire activity against 25-year historical windows to anticipate critical burning seasons and allocate suppression resources.',
  },
  {
    icon: FlaskConical,
    title: 'Earth Observation Researchers',
    body: 'Inspect sensor transitions across MODIS and VIIRS, query custom areas of interest, and download clean CSV slices without manual GIS wrangling.',
  },
  {
    icon: Trees,
    title: 'Protected Area & Land Managers',
    body: 'Track recurring agricultural burns, land-clearing cycles, and wildfire anomalies inside parks and ecological corridors.',
  },
] as const
</script>

<template>
  <section id="audience" class="py-16 sm:py-20">
    <div class="mx-auto max-w-6xl px-4 sm:px-6">
      <div class="max-w-2xl space-y-3">
        <p class="font-mono text-xs uppercase tracking-wider text-accent">Who It’s For</p>
        <h2 class="text-2xl font-bold tracking-tight text-ink-primary sm:text-3xl">
          Built for Operational Clarity and Scientific Honesty
        </h2>
      </div>

      <div class="mt-10 grid gap-5 md:grid-cols-3">
        <article
          v-for="item in audiences"
          :key="item.title"
          class="rounded-xl border border-border-subtle bg-surface-panel p-6"
        >
          <component :is="item.icon" aria-hidden="true" class="mb-4 h-5 w-5 text-accent-bright" />
          <h3 class="text-base font-semibold text-ink-primary">{{ item.title }}</h3>
          <p class="mt-2 text-sm leading-relaxed text-ink-muted">{{ item.body }}</p>
        </article>
      </div>

      <div
        class="mt-10 flex flex-col items-start justify-between gap-6 rounded-2xl border border-border-strong bg-surface-panel p-6 sm:flex-row sm:items-center sm:p-8"
      >
        <div class="max-w-2xl space-y-2">
          <p class="font-mono text-xs uppercase tracking-wider text-accent-bright">
            Current Prototype Scope
          </p>
          <h3 class="text-lg font-semibold text-ink-primary">
            Explore the Nicaragua 2000–2025 Demonstration Archive
          </h3>
          <p class="text-sm leading-relaxed text-ink-muted">
            The interactive dashboard loads a 5,000-point Nicaragua 2024 map sample alongside the
            full 2000–2025 national monthly calendar (800,480 raw detections). Harmonization weights
            are actively under scientific validation.
          </p>
        </div>

        <RouterLink
          :to="{ name: 'dashboard' }"
          class="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-surface-base transition hover:bg-accent-bright focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <span>Open Dashboard</span>
          <ArrowRight aria-hidden="true" class="h-4 w-4" />
        </RouterLink>
      </div>
    </div>
  </section>
</template>
