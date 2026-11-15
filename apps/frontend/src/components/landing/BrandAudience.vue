<script setup lang="ts">
import { Compass, Microscope, Trees } from '@lucide/vue'

const audiences = [
  {
    icon: Compass,
    title: 'La curiosidad es suficiente.',
    audience: 'Aficionados y estudiantes',
    body: 'Acércate a la observación satelital y explora la actividad de fuego sin conocimientos geoespaciales avanzados. Las explicaciones te acompañan en cada paso.',
  },
  {
    icon: Microscope,
    title: 'Más espacio para investigar.',
    audience: 'Investigación y docencia',
    body: 'Estudiantes, docentes e investigadores: consulta el histórico, revisa las fuentes y descarga los datos en CSV para tus clases, análisis y proyectos.',
  },
  {
    icon: Trees,
    title: 'El territorio, con contexto.',
    audience: 'Gestión ambiental y prevención',
    body: 'Analistas ambientales, áreas protegidas, bomberos y equipos de prevención: identifica patrones, anomalías y temporadas críticas para planificar.',
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
      <div class="landing-section-heading">
        <h2 id="community-title">La ciencia empieza<br /><span>con tu curiosidad.</span></h2>
        <p>
          Hay muchas formas de mirar un territorio. PyroTrace acerca la observación satelital a
          quienes quieren aprender, investigar y planificar.
        </p>
      </div>
      <div class="landing-audiences">
        <article v-for="audience in audiences" :key="audience.audience" class="landing-audience">
          <div class="landing-audience-icon">
            <component :is="audience.icon" :size="29" :stroke-width="1.5" aria-hidden="true" />
          </div>
          <span class="landing-audience-who">{{ audience.audience }}</span>
          <h3>{{ audience.title }}</h3>
          <p>{{ audience.body }}</p>
        </article>
      </div>
      <div class="landing-purpose">
        <div>
          <h3>Misión</h3>
          <p>
            Facilitar el acceso gratuito y la comprensión de datos satelitales sobre la actividad de
            fuego, integrando y armonizando registros MODIS y VIIRS mediante mapas y calendarios
            intuitivos que ayuden a aficionados, estudiantes, investigadores y responsables
            ambientales a identificar patrones, anomalías y periodos críticos para apoyar la
            planificación preventiva.
          </p>
        </div>
        <div>
          <h3>Visión</h3>
          <p>
            Ser una plataforma de referencia que conecte datos satelitales de distintas generaciones
            y los transforme en información clara, comparable y accesible, permitiendo a personas y
            organizaciones comprender la actividad de fuego y fortalecer la investigación, la
            planificación preventiva y la gestión del territorio.
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
