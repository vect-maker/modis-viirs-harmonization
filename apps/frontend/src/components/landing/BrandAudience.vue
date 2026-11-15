<script setup lang="ts">
import { Compass, Microscope, Trees, Plus } from '@lucide/vue'

const audiences = [
  {
    number: '01',
    icon: Compass,
    title: 'La curiosidad es suficiente.',
    audience: 'AFICIONADOS Y ESTUDIANTES',
    body: 'Acércate a la observación satelital, conoce los sensores y explora la actividad de fuego con una interfaz fácil de entender.',
  },
  {
    number: '02',
    icon: Microscope,
    title: 'Más espacio para investigar.',
    audience: 'INVESTIGACIÓN Y DOCENCIA',
    body: 'Consulta los registros, revisa sus fuentes y descarga datos para tus propias preguntas, análisis y proyectos.',
  },
  {
    number: '03',
    icon: Trees,
    title: 'El territorio, con contexto.',
    audience: 'GESTIÓN AMBIENTAL Y PREVENCIÓN',
    body: 'Examina patrones y temporadas de actividad para aportar contexto a la planificación y al cuidado del territorio.',
  },
]
</script>

<template>
  <section
    id="comunidad"
    class="landing-section landing-community"
    aria-labelledby="community-title"
  >
    <div class="landing-wrap">
      <div class="landing-section-top">
        <span class="landing-section-index">03 / COMPARTIR</span
        ><span class="landing-section-note">CIENCIA ABIERTA, ACCESO CERCANO</span>
      </div>
      <div class="landing-section-heading">
        <h2 id="community-title">La ciencia empieza<br /><span>con tu curiosidad.</span></h2>
        <p>
          Hay muchas formas de mirar un territorio. PyroTrace acerca la observación satelital a
          quienes quieren aprender, investigar y planificar.
        </p>
      </div>
      <div class="landing-audiences">
        <article v-for="audience in audiences" :key="audience.number" class="landing-audience">
          <div class="landing-audience-icon">
            <component
              :is="audience.icon"
              :size="29"
              :stroke-width="1.5"
              aria-hidden="true"
            /><span>{{ audience.number }}</span>
          </div>
          <span class="landing-kicker">{{ audience.audience }}</span>
          <h3>{{ audience.title }}</h3>
          <p>{{ audience.body }}</p>
        </article>
      </div>
      <div class="landing-purpose">
        <details>
          <summary>
            <span><span class="landing-kicker">NUESTRO PROPÓSITO</span><strong>Misión</strong></span
            ><Plus :size="21" aria-hidden="true" />
          </summary>
          <p>
            Facilitar el acceso gratuito y la comprensión de datos satelitales sobre la actividad de
            fuego, integrando y armonizando registros MODIS y VIIRS mediante mapas y calendarios
            intuitivos que ayuden a aficionados, estudiantes, investigadores y responsables
            ambientales a identificar patrones, anomalías y periodos críticos para apoyar la
            planificación preventiva.
          </p>
        </details>
        <details>
          <summary>
            <span
              ><span class="landing-kicker">EL FUTURO QUE BUSCAMOS</span
              ><strong>Visión</strong></span
            ><Plus :size="21" aria-hidden="true" />
          </summary>
          <p>
            Ser una plataforma de referencia que conecte datos satelitales de distintas generaciones
            y los transforme en información clara, comparable y accesible, permitiendo a personas y
            organizaciones comprender la actividad de fuego y fortalecer la investigación, la
            planificación preventiva y la gestión del territorio.
          </p>
        </details>
      </div>
    </div>
  </section>
</template>
