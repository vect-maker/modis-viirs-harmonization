<script setup lang="ts">
import { computed } from 'vue'
import { Plus } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const questions = computed(() =>
  [0, 1, 2, 3, 4, 5, 6].map((i) => ({
    title: t(`landing.questions.items.${i}.title`),
    text: t(`landing.questions.items.${i}.text`),
  })),
)
</script>

<template>
  <section
    id="preguntas"
    class="landing-section landing-questions"
    aria-labelledby="questions-title"
  >
    <div class="landing-wrap landing-questions-grid">
      <div class="landing-questions-intro">
        <h2 id="questions-title">
          {{ t('landing.questions.titleLine1') }}<br /><span>{{
            t('landing.questions.titleHighlight')
          }}</span>
        </h2>
        <p>
          {{ t('landing.questions.subtitle') }}
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
