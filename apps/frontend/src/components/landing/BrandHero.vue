<script setup lang="ts">
import { ArrowDown, ArrowUpRight, Check } from '@lucide/vue'
import BrandMap from './BrandMap.vue'
</script>

<template>
  <section class="landing-hero" aria-labelledby="landing-title">
    <div class="landing-wrap landing-hero-grid">
      <div class="landing-hero-copy">
        <h1 id="landing-title" class="landing-entrance">
          Datos satelitales<br />para comprender<br /><span>el fuego.</span>
        </h1>
        <p class="landing-hero-description landing-entrance landing-delay-2">
          Explora dónde y cuándo se concentra la actividad de fuego en Centroamérica. Más de 25 años
          de detecciones MODIS y VIIRS, armonizadas para compararlas en mapas, calendarios y
          estadísticas.
        </p>
        <div class="landing-hero-actions landing-entrance landing-delay-3">
          <RouterLink :to="{ name: 'dashboard' }" class="landing-button"
            >Abrir explorador <ArrowUpRight :size="19" aria-hidden="true"
          /></RouterLink>
          <a href="#proyecto" class="landing-text-link"
            >Conocer el proyecto <ArrowDown :size="17" aria-hidden="true"
          /></a>
        </div>
        <div class="landing-hero-assurance landing-entrance landing-delay-3">
          <span><Check :size="15" aria-hidden="true" /> Gratis y sin registro</span
          ><span><Check :size="15" aria-hidden="true" /> Sin ser experto en mapas</span
          ><span><Check :size="15" aria-hidden="true" /> Datos descargables en CSV</span>
        </div>
      </div>
      <div class="landing-hero-visual landing-entrance landing-delay-2"><BrandMap /></div>
      <div class="landing-hero-bottom">
        <span>Desarrollado para NASA Space Apps 2026</span
        ><a href="#proyecto" aria-label="Continuar hacia el proyecto"
          ><ArrowDown :size="18" aria-hidden="true" /></a
        ><span>Los siete países de Centroamérica, desde 2000</span>
      </div>
    </div>
  </section>
</template>
