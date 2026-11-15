<script setup lang="ts">
import { ArrowDown, ArrowRight, Layers3, ScanLine } from '@lucide/vue'
</script>

<template>
  <section
    id="proyecto"
    class="landing-section landing-continuity"
    aria-labelledby="continuity-title"
  >
    <div class="landing-wrap">
      <div class="landing-section-top">
        <span class="landing-section-index">01 / CONECTAR</span
        ><span class="landing-section-note">EL RETO MODIS–VIIRS</span>
      </div>
      <div class="landing-section-heading">
        <h2 id="continuity-title">Dos sensores.<br /><span>Un análisis continuo.</span></h2>
        <p>
          Los satélites cambian. Comprender el territorio requiere conectar sus observaciones y
          tener en cuenta sus diferencias.
        </p>
      </div>
      <div class="landing-sensor-story">
        <article class="landing-sensor-column">
          <div class="landing-sensor-name">
            <span class="landing-sensor-symbol"><Layers3 :size="26" aria-hidden="true" /></span>
            <div>
              <span class="landing-kicker">EL REGISTRO QUE NOS PRECEDE</span>
              <h3>MODIS</h3>
            </div>
            <span class="landing-resolution">~1 km</span>
          </div>
          <div
            class="landing-resolution-grid landing-grid-coarse"
            role="img"
            aria-label="Esquema de una cuadrícula MODIS de aproximadamente un kilómetro"
          >
            <i v-for="n in 24" :key="n" :class="{ active: [8, 9, 14, 15].includes(n) }" />
          </div>
          <p>Más de dos décadas de observaciones para estudiar cómo varía la actividad de fuego.</p>
        </article>
        <div class="landing-sensor-join" aria-hidden="true">
          <ArrowRight :size="22" /><span>+</span>
        </div>
        <article class="landing-sensor-column">
          <div class="landing-sensor-name">
            <span class="landing-sensor-symbol landing-sensor-symbol-blue"
              ><ScanLine :size="26" aria-hidden="true"
            /></span>
            <div>
              <span class="landing-kicker">LA CONTINUIDAD CON MÁS DETALLE</span>
              <h3>VIIRS</h3>
            </div>
            <span class="landing-resolution">375 m</span>
          </div>
          <div
            class="landing-resolution-grid landing-grid-fine"
            role="img"
            aria-label="Esquema de una cuadrícula VIIRS de 375 metros, con mayor detalle espacial"
          >
            <i
              v-for="n in 160"
              :key="n"
              :class="{
                active: [51, 52, 67, 68, 69, 83, 84, 85, 86, 98, 99, 100, 101, 115, 116].includes(
                  n,
                ),
              }"
            />
          </div>
          <p>
            Una resolución y sensibilidad diferentes que requieren cuidado al comparar los datos.
          </p>
        </article>
      </div>
      <div class="landing-harmonization-line">
        <div class="landing-merge-icon" aria-hidden="true"><ArrowDown :size="18" /></div>
        <p>
          <strong>Armonizar es hacer comparables esas observaciones.</strong> Es el trabajo
          científico que estamos desarrollando y validando.
        </p>
        <a href="#datos" class="landing-text-link"
          >Ver el calendario <ArrowDown :size="17" aria-hidden="true"
        /></a>
      </div>
    </div>
  </section>
</template>
