<script setup lang="ts">
import { ArrowDown, ArrowUpRight, Check } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import BrandMap from './BrandMap.vue'

const { t } = useI18n()
</script>

<template>
  <section class="landing-hero" aria-labelledby="landing-title">
    <div class="landing-wrap landing-hero-grid">
      <div class="landing-hero-copy">
        <h1 id="landing-title" class="landing-entrance">
          {{ t('landing.hero.titleLine1') }}<br />{{ t('landing.hero.titleLine2') }}<br /><span>{{
            t('landing.hero.titleHighlight')
          }}</span>
        </h1>
        <p class="landing-hero-description landing-entrance landing-delay-2">
          {{ t('landing.hero.description') }}
        </p>
        <div class="landing-hero-actions landing-entrance landing-delay-3">
          <RouterLink :to="{ name: 'dashboard' }" class="landing-button"
            >{{ t('nav.openExplorer') }} <ArrowUpRight :size="19" aria-hidden="true"
          /></RouterLink>
          <a href="#proyecto" class="landing-text-link"
            >{{ t('landing.hero.aboutProject') }} <ArrowDown :size="17" aria-hidden="true"
          /></a>
        </div>
        <div class="landing-hero-assurance landing-entrance landing-delay-3">
          <span><Check :size="15" aria-hidden="true" /> {{ t('landing.hero.assuranceFree') }}</span
          ><span
            ><Check :size="15" aria-hidden="true" />
            {{ t('landing.hero.assuranceAccessible') }}</span
          ><span><Check :size="15" aria-hidden="true" /> {{ t('landing.hero.assuranceCsv') }}</span>
        </div>
      </div>
      <div class="landing-hero-visual landing-entrance landing-delay-2"><BrandMap /></div>
      <div class="landing-hero-bottom">
        <span>{{ t('landing.hero.builtFor') }}</span
        ><a href="#proyecto" :aria-label="t('landing.hero.continueAria')"
          ><ArrowDown :size="18" aria-hidden="true" /></a
        ><span>{{ t('landing.hero.coverage') }}</span>
      </div>
    </div>
  </section>
</template>
