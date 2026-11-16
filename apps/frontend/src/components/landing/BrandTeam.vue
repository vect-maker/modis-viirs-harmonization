<script setup lang="ts">
import { ArrowUpRight } from '@lucide/vue'

const pillars = [
  {
    title: 'Integration & continuity',
    text: 'We bridge MODIS and VIIRS so sensor differences do not break long-term analysis.',
  },
  {
    title: 'Clarity',
    text: 'We turn complex satellite archives into readable maps and calendars.',
  },
  {
    title: 'Accessibility',
    text: 'A free, approachable experience for everyone from curious learners to institutions.',
  },
  {
    title: 'Rigor & transparency',
    text: 'We validate our methods and clearly document data provenance and ongoing work.',
  },
  {
    title: 'Actionable insight',
    text: 'We help decision-makers recognize patterns, anomalies, and critical fire seasons.',
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
        <h2 id="team-title">A NASA challenge,<br />built from Managua.</h2>
        <p>
          PyroTrace was created for the <strong>MODIS and VIIRS hot spots</strong> challenge at NASA
          Space Apps 2026: bridging two generations of sensors so fire activity can be compared
          consistently over time and explored by anyone.
        </p>
        <a
          href="https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/?tab=details"
          target="_blank"
          rel="noopener noreferrer"
          class="landing-text-link"
          >Read the challenge <ArrowUpRight :size="17" aria-hidden="true"
        /></a>
        <a
          href="https://www.spaceappschallenge.org/2026/find-a-team/sdlg/?tab=members"
          target="_blank"
          rel="noopener noreferrer"
          class="landing-text-link"
          >View team on Space Apps <ArrowUpRight :size="17" aria-hidden="true"
        /></a>
      </div>
      <div class="landing-team-people">
        <h3>The Team</h3>
        <ul>
          <li v-for="name in team" :key="name">{{ name }}</li>
        </ul>
      </div>
      <div class="landing-pillars">
        <h3>What guides us</h3>
        <dl>
          <div v-for="pillar in pillars" :key="pillar.title">
            <dt>{{ pillar.title }}</dt>
            <dd>{{ pillar.text }}</dd>
          </div>
        </dl>
        <p class="landing-pillars-partners">
          We build on open NASA FIRMS data and welcome collaborators across universities,
          environmental agencies, conservation groups, and technology partners.
        </p>
      </div>
    </div>
  </section>
</template>
