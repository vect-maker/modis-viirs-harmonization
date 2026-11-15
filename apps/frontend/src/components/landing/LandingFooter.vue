<script setup lang="ts">
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'
</script>

<template>
  <footer class="border-t border-border-subtle bg-surface-input/60 py-8">
    <div
      class="mx-auto flex max-w-6xl flex-col items-start justify-between gap-4 px-4 text-xs text-ink-muted sm:flex-row sm:items-center sm:px-6"
    >
      <div class="flex items-center gap-2 text-ink-secondary">
        <PyroTraceLogo class="h-5 w-auto" />
        <span>· NASA Space Apps Challenge 2026</span>
      </div>
      <p>
        Active fire data sourced from NASA FIRMS / Earthdata (MODIS &amp; VIIRS). Open-source
        prototype.
      </p>
      <RouterLink
        :to="{ name: 'dashboard' }"
        class="font-medium text-accent-bright hover:underline focus-visible:outline-2 focus-visible:outline-focus"
      >
        /dashboard
      </RouterLink>
    </div>
  </footer>
</template>
