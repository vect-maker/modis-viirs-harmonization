<script setup lang="ts">
import BrandHeader from '@/components/landing/BrandHeader.vue'
import BrandHero from '@/components/landing/BrandHero.vue'
import BrandContinuity from '@/components/landing/BrandContinuity.vue'
import BrandCalendar from '@/components/landing/BrandCalendar.vue'
import BrandAudience from '@/components/landing/BrandAudience.vue'
import BrandQuestions from '@/components/landing/BrandQuestions.vue'
import BrandFooter from '@/components/landing/BrandFooter.vue'
import '@/assets/landing.css'
</script>

<template>
  <div class="pyro-landing" lang="es">
    <a class="landing-skip" href="#contenido">Saltar al contenido</a>
    <BrandHeader />
    <main id="contenido" tabindex="-1">
      <BrandHero />
      <BrandContinuity />
      <BrandCalendar />
      <BrandAudience />
      <BrandQuestions />
    </main>
    <BrandFooter />
  </div>
</template>
