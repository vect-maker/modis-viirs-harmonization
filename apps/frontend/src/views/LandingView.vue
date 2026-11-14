<script setup lang="ts">
import LandingNavbar from '@/components/landing/LandingNavbar.vue'
import LandingHero from '@/components/landing/LandingHero.vue'
import LandingProblem from '@/components/landing/LandingProblem.vue'
import LandingMethodology from '@/components/landing/LandingMethodology.vue'
import LandingAudience from '@/components/landing/LandingAudience.vue'
import LandingFooter from '@/components/landing/LandingFooter.vue'
</script>

<template>
  <div
    class="min-h-dvh bg-surface-base font-sans text-ink-primary selection:bg-accent selection:text-surface-base"
  >
    <LandingNavbar />
    <main>
      <LandingHero />
      <LandingProblem />
      <LandingMethodology />
      <LandingAudience />
    </main>
    <LandingFooter />
  </div>
</template>
