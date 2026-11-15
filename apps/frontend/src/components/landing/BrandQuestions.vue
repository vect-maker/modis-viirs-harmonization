<script setup lang="ts">
import { Plus } from '@lucide/vue'

const questions = [
  {
    title: '¿Qué puedo consultar en el explorador?',
    text: 'Las detecciones de los siete países de Centroamérica desde noviembre de 2000, en un mapa con filtros por fecha, sensor y área dibujada. El panel de estadísticas compara cada mes con su rango histórico y muestra la actividad por año, en conteo crudo o armonizado.',
  },
  {
    title: '¿Qué significa armonizar MODIS y VIIRS?',
    text: 'Llevar las detecciones de los dos sensores a una misma unidad, detecciones equivalentes VIIRS, para que un año de 2005 se pueda comparar con uno de 2024. El método está explicado más arriba y sigue en validación.',
  },
  {
    title: '¿Por qué los datos de 2026 se ven distintos?',
    text: 'Desde 2026 los datos llegan casi en tiempo real y todavía no pasan por la armonización. Por eso el explorador los marca aparte y no los usa en las comparaciones con años anteriores.',
  },
  {
    title: '¿Una detección es un incendio?',
    text: 'No. Es un píxel donde el satélite midió calor anómalo. Un incendio grande puede dejar muchas detecciones y uno pequeño puede no aparecer.',
  },
  {
    title: '¿Necesito conocimientos técnicos?',
    text: 'Puedes empezar con curiosidad: selecciona un periodo, observa los patrones y consulta las explicaciones. La plataforma está pensada tanto para aficionados y estudiantes como para investigadores y responsables ambientales.',
  },
  {
    title: '¿La plataforma es gratuita?',
    text: 'Sí. Puedes explorar sin crear una cuenta y descargar en CSV las detecciones que filtres. Usamos datos abiertos de NASA FIRMS y explicamos de dónde vienen y hasta dónde llegan.',
  },
  {
    title: '¿Cómo se sostiene PyroTrace?',
    text: 'El acceso seguirá siendo gratuito. Buscamos sostenerlo con donaciones voluntarias, fondos de innovación e investigación ambiental, patrocinios tecnológicos y convenios con universidades y organizaciones.',
  },
]
</script>

<template>
  <section
    id="preguntas"
    class="landing-section landing-questions"
    aria-labelledby="questions-title"
  >
    <div class="landing-wrap landing-questions-grid">
      <div class="landing-questions-intro">
        <h2 id="questions-title">Las preguntas<br /><span>también importan.</span></h2>
        <p>
          La claridad empieza por explicar qué hacemos, qué muestran los datos y hasta dónde llegan.
        </p>
      </div>
      <div class="landing-faq-list">
        <details v-for="question in questions" :key="question.title">
          <summary>{{ question.title }}<Plus :size="21" aria-hidden="true" /></summary>
          <p>{{ question.text }}</p>
        </details>
      </div>
    </div>
  </section>
</template>
