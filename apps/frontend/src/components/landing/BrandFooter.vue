<script setup lang="ts">
import { ArrowUpRight, ArrowUp } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'

const { t } = useI18n()
</script>

<template>
  <footer class="landing-footer">
    <div class="landing-wrap">
      <div class="landing-footer-top">
        <a href="#landing-title" class="landing-icon-link" :aria-label="t('landing.footer.backToTop')"
          ><ArrowUp :size="19" aria-hidden="true"
        /></a>
      </div>
      <div class="landing-footer-callout">
        <h2>
          {{ t('landing.footer.calloutLine1') }}<br /><span>{{
            t('landing.footer.calloutHighlight')
          }}</span>
        </h2>
        <div>
          <p>
            {{ t('landing.footer.calloutSub1') }}<br />{{ t('landing.footer.calloutSub2') }}
          </p>
          <RouterLink :to="{ name: 'dashboard' }" class="landing-button"
            >{{ t('nav.openExplorer') }} <ArrowUpRight :size="19" aria-hidden="true"
          /></RouterLink>
        </div>
      </div>
      <div class="landing-footer-brand">
        <PyroTraceLogo />
        <p>
          {{ t('landing.footer.brandLine1') }}<br />{{ t('landing.footer.brandLine2') }}
        </p>
      </div>
      <div class="landing-footer-bottom">
        <p>{{ t('landing.footer.copyright') }}</p>
        <nav :aria-label="t('landing.footer.sourcesAria')">
          <a href="https://firms.modaps.eosdis.nasa.gov/" target="_blank" rel="noopener noreferrer"
            >{{ t('landing.footer.nasaFirms') }} <ArrowUpRight :size="13" aria-hidden="true" /></a
          ><a
            href="https://www.naturalearthdata.com/about/terms-of-use/"
            target="_blank"
            rel="noopener noreferrer"
            >{{ t('landing.footer.naturalEarth') }} <ArrowUpRight :size="13" aria-hidden="true" /></a
          ><a
            href="https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/?tab=details"
            target="_blank"
            rel="noopener noreferrer"
            >{{ t('landing.footer.theChallenge') }} <ArrowUpRight :size="13" aria-hidden="true" /></a
          ><a
            href="https://www.spaceappschallenge.org/2026/find-a-team/sdlg/?tab=members"
            target="_blank"
            rel="noopener noreferrer"
            >{{ t('landing.footer.teamSpaceApps') }} <ArrowUpRight :size="13" aria-hidden="true"
          /></a>
        </nav>
      </div>
    </div>
  </footer>
</template>
