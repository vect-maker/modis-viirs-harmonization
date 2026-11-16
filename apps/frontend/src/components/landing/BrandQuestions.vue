<script setup lang="ts">
import { Plus } from '@lucide/vue'

const questions = [
  {
    title: 'What can I explore in the dashboard?',
    text: 'Fire detections across all seven Central American countries since November 2000, on an interactive map with filters by date, sensor, and drawn area. The statistics panel compares each month against its historical range and shows annual activity as raw counts or harmonized index.',
  },
  {
    title: 'What does harmonizing MODIS and VIIRS mean?',
    text: 'Converting detections from both sensors onto a common scale—VIIRS-equivalent detections—so a year like 2005 can be compared fairly against 2024. The method is outlined above and remains under active validation.',
  },
  {
    title: 'Why do 2026 records look different?',
    text: 'Near-real-time detections from 2026 have not yet passed through the historical harmonization pipeline. The explorer marks them separately as provisional and excludes them from multi-year baseline comparisons.',
  },
  {
    title: 'Is every detection a separate fire?',
    text: 'No. Each detection is a satellite pixel showing anomalous thermal radiation. One large wildfire can produce many detections, while small or cloud-obscured fires may not be captured.',
  },
  {
    title: 'Do I need technical expertise?',
    text: 'Not at all. Start with curiosity: pick a period, inspect the patterns, and read the in-app guides. PyroTrace is built for students and enthusiasts as well as researchers and emergency planners.',
  },
  {
    title: 'Is the platform free?',
    text: 'Yes. You can explore without an account and export filtered detections to CSV. We use open NASA FIRMS data and document data provenance and limitations clearly.',
  },
  {
    title: 'How is PyroTrace sustained?',
    text: 'Core access remains free. Long-term sustainability relies on community donations, environmental research and innovation grants, technology sponsorships, and partnerships with universities and agencies.',
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
        <h2 id="questions-title">Questions<br /><span>matter too.</span></h2>
        <p>
          Clarity starts with explaining how the data works, what it shows, and where its limits
          are.
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
