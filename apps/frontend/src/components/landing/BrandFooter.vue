<script setup lang="ts">
import { ArrowUpRight, ArrowUp } from '@lucide/vue'
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'
</script>

<template>
  <footer class="landing-footer">
    <div class="landing-wrap">
      <div class="landing-footer-top">
        <span class="landing-eyebrow"
          ><span class="landing-status-dot" /> TU TERRITORIO. TUS PREGUNTAS.</span
        ><a href="#landing-title" class="landing-icon-link" aria-label="Volver al inicio"
          ><ArrowUp :size="19" aria-hidden="true"
        /></a>
      </div>
      <div class="landing-footer-callout">
        <h2>Una mirada más clara.<br /><span>Empieza en el mapa.</span></h2>
        <div>
          <p>Conecta con los datos.<br />Comprende lo que observas.</p>
          <RouterLink :to="{ name: 'dashboard' }" class="landing-button"
            >Abrir explorador <ArrowUpRight :size="19" aria-hidden="true"
          /></RouterLink>
        </div>
      </div>
      <div class="landing-footer-brand">
        <PyroTraceLogo />
        <p>Conectamos datos satelitales<br />para comprender y decidir mejor.</p>
      </div>
      <div class="landing-footer-bottom">
        <p>PyroTrace · NASA Space Apps Challenge 2026</p>
        <nav aria-label="Fuentes del proyecto">
          <a href="https://firms.modaps.eosdis.nasa.gov/" target="_blank" rel="noopener noreferrer"
            >Datos NASA FIRMS <ArrowUpRight :size="13" aria-hidden="true" /></a
          ><a
            href="https://www.naturalearthdata.com/about/terms-of-use/"
            target="_blank"
            rel="noopener noreferrer"
            >Cartografía Natural Earth <ArrowUpRight :size="13" aria-hidden="true" /></a
          ><a
            href="https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/?tab=details"
            target="_blank"
            rel="noopener noreferrer"
            >El reto <ArrowUpRight :size="13" aria-hidden="true"
          /></a>
        </nav>
      </div>
    </div>
  </footer>
</template>
