<script setup lang="ts">
import { computed } from 'vue'
import { ArrowUpRight } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const pillars = computed(() =>
  [0, 1, 2, 3, 4].map((i) => ({
    title: t(`landing.team.pillars.${i}.title`),
    text: t(`landing.team.pillars.${i}.text`),
  })),
)

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
        <h2 id="team-title">
          {{ t('landing.team.titleLine1') }}<br />{{ t('landing.team.titleLine2') }}
        </h2>
        <p>
          {{ t('landing.team.bodyBefore') }}
          <strong>{{ t('landing.team.bodyStrong') }}</strong>
          {{ t('landing.team.bodyAfter') }}
        </p>
        <a
          href="https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/?tab=details"
          target="_blank"
          rel="noopener noreferrer"
          class="landing-text-link"
          >{{ t('landing.team.readChallenge') }} <ArrowUpRight :size="17" aria-hidden="true"
        /></a>
        <a
          href="https://www.spaceappschallenge.org/2026/find-a-team/sdlg/?tab=members"
          target="_blank"
          rel="noopener noreferrer"
          class="landing-text-link"
          >{{ t('landing.team.viewTeam') }} <ArrowUpRight :size="17" aria-hidden="true"
        /></a>
      </div>
      <div class="landing-team-people">
        <h3>{{ t('landing.team.theTeam') }}</h3>
        <ul>
          <li v-for="name in team" :key="name">{{ name }}</li>
        </ul>
      </div>
      <div class="landing-pillars">
        <h3>{{ t('landing.team.whatGuidesUs') }}</h3>
        <dl>
          <div v-for="pillar in pillars" :key="pillar.title">
            <dt>{{ pillar.title }}</dt>
            <dd>{{ pillar.text }}</dd>
          </div>
        </dl>
        <p class="landing-pillars-partners">
          {{ t('landing.team.partners') }}
        </p>
      </div>
    </div>
  </section>
</template>
