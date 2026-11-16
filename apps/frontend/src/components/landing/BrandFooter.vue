<script setup lang="ts">
import { ArrowUpRight, ArrowUp } from '@lucide/vue'
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'
</script>

<template>
  <footer class="landing-footer">
    <div class="landing-wrap">
      <div class="landing-footer-top">
        <a href="#landing-title" class="landing-icon-link" aria-label="Back to top"
          ><ArrowUp :size="19" aria-hidden="true"
        /></a>
      </div>
      <div class="landing-footer-callout">
        <h2>A clearer view.<br /><span>Starts on the map.</span></h2>
        <div>
          <p>Connect with the data.<br />Understand what you observe.</p>
          <RouterLink :to="{ name: 'dashboard' }" class="landing-button"
            >Open Explorer <ArrowUpRight :size="19" aria-hidden="true"
          /></RouterLink>
        </div>
      </div>
      <div class="landing-footer-brand">
        <PyroTraceLogo />
        <p>Connecting satellite records<br />for clearer decisions.</p>
      </div>
      <div class="landing-footer-bottom">
        <p>PyroTrace, NASA Space Apps Challenge 2026</p>
        <nav aria-label="Project sources">
          <a href="https://firms.modaps.eosdis.nasa.gov/" target="_blank" rel="noopener noreferrer"
            >NASA FIRMS Data <ArrowUpRight :size="13" aria-hidden="true" /></a
          ><a
            href="https://www.naturalearthdata.com/about/terms-of-use/"
            target="_blank"
            rel="noopener noreferrer"
            >Natural Earth Basemaps <ArrowUpRight :size="13" aria-hidden="true" /></a
          ><a
            href="https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/?tab=details"
            target="_blank"
            rel="noopener noreferrer"
            >The Challenge <ArrowUpRight :size="13" aria-hidden="true" /></a
          ><a
            href="https://www.spaceappschallenge.org/2026/find-a-team/sdlg/?tab=members"
            target="_blank"
            rel="noopener noreferrer"
            >Team on Space Apps <ArrowUpRight :size="13" aria-hidden="true"
          /></a>
        </nav>
      </div>
    </div>
  </footer>
</template>
