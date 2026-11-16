<script setup lang="ts">
import { Compass, Microscope, Trees } from '@lucide/vue'

const audiences = [
  {
    icon: Compass,
    title: 'Curiosity is enough.',
    audience: 'Enthusiasts & students',
    body: 'Get started with satellite Earth observation and explore fire activity without advanced GIS training. Clear explanations guide you at every step.',
  },
  {
    icon: Microscope,
    title: 'More room to investigate.',
    audience: 'Research & education',
    body: 'Students, educators, and researchers: explore the historical record, inspect data sources, and export filtered CSV datasets for classes and studies.',
  },
  {
    icon: Trees,
    title: 'Territory, with context.',
    audience: 'Environmental & fire management',
    body: 'Environmental analysts, protected-area teams, firefighters, and emergency planners: spot patterns, anomalies, and critical seasons to guide preparedness.',
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
        <h2 id="community-title">Science begins<br /><span>with curiosity.</span></h2>
        <p>
          There are many ways to look at a landscape. PyroTrace brings satellite observation closer
          to everyone who wants to learn, investigate, and plan.
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
          <h3>Mission</h3>
          <p>
            Provide free access to and clear understanding of satellite fire-activity data by
            integrating and harmonizing MODIS and VIIRS records through intuitive maps and calendars
            that help enthusiasts, students, researchers, and environmental managers identify
            patterns, anomalies, and critical periods for preventive planning.
          </p>
        </div>
        <div>
          <h3>Vision</h3>
          <p>
            Become a reference platform that bridges multi-generation satellite records and turns
            them into clear, comparable, and accessible intelligence—empowering people and
            organizations to understand fire activity and strengthen research, preparedness, and
            land management.
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
