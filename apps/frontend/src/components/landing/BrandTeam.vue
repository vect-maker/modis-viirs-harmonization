<script setup lang="ts">
import { ArrowUpRight } from '@lucide/vue'

const pillars = [
  {
    title: 'Integración y continuidad',
    text: 'Conectamos MODIS y VIIRS para que sus diferencias no corten el análisis.',
  },
  { title: 'Claridad', text: 'Convertimos datos complejos en mapas y calendarios fáciles de leer.' },
  {
    title: 'Accesibilidad',
    text: 'Una experiencia gratuita y amigable, de aficionados a instituciones.',
  },
  {
    title: 'Rigor y transparencia',
    text: 'Validamos los métodos y decimos de dónde vienen los datos y qué sigue en validación.',
  },
  {
    title: 'Utilidad para decidir',
    text: 'Ayudamos a reconocer patrones, anomalías y temporadas críticas.',
  },
]

const team = [
  'Jose Miranda',
  'Inti Montalvan',
  'Joshua Ordóñez',
  'Fernando Gómez',
  'Geovanny Miranda',
  'Herman Rodríguez',
]
</script>

<template>
  <section id="equipo" class="landing-section landing-team" aria-labelledby="team-title">
    <div class="landing-wrap landing-team-grid">
      <div class="landing-team-challenge">
        <h2 id="team-title">Un reto de la NASA,<br />trabajado desde Managua.</h2>
        <p>
          PyroTrace nace del reto <strong>MODIS and VIIRS hot spots</strong> de NASA Space Apps
          2026: unir dos generaciones de sensores para que la actividad de fuego se pueda comparar
          a lo largo del tiempo, y ponerla al alcance de cualquier persona.
        </p>
        <a
          href="https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/?tab=details"
          target="_blank"
          rel="noopener noreferrer"
          class="landing-text-link"
          >Leer el reto <ArrowUpRight :size="17" aria-hidden="true"
        /></a>
        <a
          href="https://www.spaceappschallenge.org/2026/find-a-team/sdlg/?tab=members"
          target="_blank"
          rel="noopener noreferrer"
          class="landing-text-link"
          >Ver el equipo en Space Apps <ArrowUpRight :size="17" aria-hidden="true"
        /></a>
      </div>
      <div class="landing-team-people">
        <h3>El equipo</h3>
        <ul>
          <li v-for="name in team" :key="name">{{ name }}</li>
        </ul>
      </div>
      <div class="landing-pillars">
        <h3>Lo que nos guía</h3>
        <dl>
          <div v-for="pillar in pillars" :key="pillar.title">
            <dt>{{ pillar.title }}</dt>
            <dd>{{ pillar.text }}</dd>
          </div>
        </dl>
        <p class="landing-pillars-partners">
          Trabajamos con datos abiertos de NASA FIRMS y buscamos aliados: universidades,
          autoridades ambientales, organizaciones de conservación y socios tecnológicos.
        </p>
      </div>
    </div>
  </section>
</template>
