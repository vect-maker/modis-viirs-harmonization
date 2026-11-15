<script setup lang="ts">
import { Plus } from '@lucide/vue'

const questions = [
  {
    title: '¿Qué puedo consultar en el prototipo?',
    text: 'El explorador presenta una muestra de 5,000 detecciones de Nicaragua de mayo de 2024 y un calendario mensual nacional de 2000 a 2025. El mapa y el calendario tienen alcances independientes; los conteos del calendario aún no están armonizados.',
  },
  {
    title: '¿Qué significa armonizar MODIS y VIIRS?',
    text: 'Significa trabajar con las diferencias de resolución, sensibilidad y frecuencia de observación de ambos sensores para construir comparaciones consistentes. Nuestra metodología está en desarrollo y validación científica.',
  },
  {
    title: '¿Necesito conocimientos técnicos?',
    text: 'Puedes empezar con curiosidad: selecciona un periodo, observa los patrones y consulta las explicaciones. La plataforma está pensada tanto para aficionados y estudiantes como para investigadores y responsables ambientales.',
  },
  {
    title: '¿La plataforma es gratuita?',
    text: 'Sí. El prototipo es gratuito y se puede consultar sin crear una cuenta. Utilizamos datos abiertos de NASA FIRMS y explicamos su procedencia y sus limitaciones.',
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
        <span class="landing-section-index">04 / CONOCER</span>
        <h2 id="questions-title">Las preguntas<br /><span>también importan.</span></h2>
        <p>
          La claridad empieza por explicar qué hacemos, qué muestran los datos y hasta dónde llegan.
        </p>
        <span class="landing-science-signature"
          ><i class="landing-status-dot" /> CURIOSIDAD CON CRITERIO</span
        >
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
