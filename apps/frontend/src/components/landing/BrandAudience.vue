<script setup lang="ts">
import { computed } from 'vue'
import { Compass, Microscope, Trees } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const icons = [Compass, Microscope, Trees]
const audiences = computed(() =>
  icons.map((icon, i) => ({
    icon,
    id: t(`landing.audience.items.${i}.id`),
    title: t(`landing.audience.items.${i}.title`),
    audience: t(`landing.audience.items.${i}.audience`),
    body: t(`landing.audience.items.${i}.body`),
  })),
)
</script>

<template>
  <section
    id="comunidad"
    class="landing-section landing-community"
    aria-labelledby="community-title"
  >
    <div class="landing-wrap">
      <div class="landing-section-heading">
        <h2 id="community-title">
          {{ t('landing.audience.titleLine1') }}<br /><span>{{
            t('landing.audience.titleHighlight')
          }}</span>
        </h2>
        <p>
          {{ t('landing.audience.subtitle') }}
        </p>
      </div>
      <div class="landing-audiences">
        <article v-for="audience in audiences" :key="audience.id" class="landing-audience">
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
          <h3>{{ t('landing.audience.missionTitle') }}</h3>
          <p>
            {{ t('landing.audience.missionBody') }}
          </p>
        </div>
        <div>
          <h3>{{ t('landing.audience.visionTitle') }}</h3>
          <p>
            {{ t('landing.audience.visionBody') }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
