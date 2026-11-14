<script setup lang="ts">
import { Clock, Eye, Scan } from '@lucide/vue'

const challenges = [
  {
    icon: Scan,
    title: 'Spatial Resolution (~1 km vs. 375 m)',
    body: 'A single MODIS hotspot pixel can correspond to multiple VIIRS detections over the same fire front, inflating raw post-2012 counts if left unharmonized.',
  },
  {
    icon: Eye,
    title: 'Sensor Sensitivity',
    body: 'VIIRS detects smaller, cooler agricultural and understory burns that MODIS misses, creating an artificial upward trend in historical comparisons.',
  },
  {
    icon: Clock,
    title: 'Orbital Overpass Schedules',
    body: 'Terra MODIS captures late-morning burns without a direct VIIRS counterpart, while Aqua and VIIRS overlap in the afternoon—requiring time-aware alignment.',
  },
] as const
</script>

<template>
  <section id="problem" class="border-b border-border-subtle py-16 sm:py-20">
    <div class="mx-auto max-w-6xl px-4 sm:px-6">
      <div class="max-w-2xl space-y-3">
        <p class="font-mono text-xs uppercase tracking-wider text-accent">The Continuity Gap</p>
        <h2 class="text-2xl font-bold tracking-tight text-ink-primary sm:text-3xl">
          Why Raw MODIS and VIIRS Records Cannot Be Compared Directly
        </h2>
        <p class="text-sm leading-relaxed text-ink-secondary sm:text-base">
          As Terra and Aqua MODIS approach end-of-life, fire managers risk losing two decades of
          historical context unless sensor differences are accounted for explicitly.
        </p>
      </div>

      <div class="mt-10 grid gap-5 md:grid-cols-3">
        <article
          v-for="item in challenges"
          :key="item.title"
          class="rounded-xl border border-border-subtle bg-surface-panel p-6"
        >
          <div
            class="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-accent/25 bg-accent/10 text-accent"
          >
            <component :is="item.icon" aria-hidden="true" class="h-5 w-5" />
          </div>
          <h3 class="text-base font-semibold text-ink-primary">{{ item.title }}</h3>
          <p class="mt-2 text-sm leading-relaxed text-ink-muted">{{ item.body }}</p>
        </article>
      </div>
    </div>
  </section>
</template>
