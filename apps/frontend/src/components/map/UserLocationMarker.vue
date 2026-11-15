<script setup lang="ts">
import { LocateFixed } from '@lucide/vue'
</script>

<template>
  <div
    aria-label="Your current location"
    class="relative flex size-8 items-center justify-center"
  >
    <span
      class="absolute inset-0 animate-ping rounded-full bg-sky-400/40"
      aria-hidden="true"
    />
    <span
      class="relative flex size-7 items-center justify-center rounded-full border-2 border-white bg-sky-500 text-white shadow-[0_0_12px_rgba(56,189,248,0.85)]"
    >
      <LocateFixed class="size-4" :stroke-width="2.25" aria-hidden="true" />
    </span>
  </div>
</template>
