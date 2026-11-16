<script setup lang="ts">
import { ArrowDown, ArrowUpRight, Check } from '@lucide/vue'
import BrandMap from './BrandMap.vue'
</script>

<template>
  <section class="landing-hero" aria-labelledby="landing-title">
    <div class="landing-wrap landing-hero-grid">
      <div class="landing-hero-copy">
        <h1 id="landing-title" class="landing-entrance">
          Satellite data<br />to understand<br /><span>fire activity.</span>
        </h1>
        <p class="landing-hero-description landing-entrance landing-delay-2">
          Explore where and when burning activity concentrates across Central America. Over 25 years
          of MODIS and VIIRS detections, harmonized for comparison across maps, calendars, and
          statistics.
        </p>
        <div class="landing-hero-actions landing-entrance landing-delay-3">
          <RouterLink :to="{ name: 'dashboard' }" class="landing-button"
            >Open Explorer <ArrowUpRight :size="19" aria-hidden="true"
          /></RouterLink>
          <a href="#proyecto" class="landing-text-link"
            >About the project <ArrowDown :size="17" aria-hidden="true"
          /></a>
        </div>
        <div class="landing-hero-assurance landing-entrance landing-delay-3">
          <span><Check :size="15" aria-hidden="true" /> Free, no sign-up required</span
          ><span><Check :size="15" aria-hidden="true" /> Built for everyone, not just GIS experts</span
          ><span><Check :size="15" aria-hidden="true" /> Exportable CSV data</span>
        </div>
      </div>
      <div class="landing-hero-visual landing-entrance landing-delay-2"><BrandMap /></div>
      <div class="landing-hero-bottom">
        <span>Built for NASA Space Apps 2026</span
        ><a href="#proyecto" aria-label="Continue to the project"
          ><ArrowDown :size="18" aria-hidden="true" /></a
        ><span>All seven Central American countries, since 2000</span>
      </div>
    </div>
  </section>
</template>
