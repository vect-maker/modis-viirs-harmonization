<script setup lang="ts">
import { TooltipProvider } from 'reka-ui'
import { RouterView } from 'vue-router'
</script>

<template>
  <TooltipProvider :delay-duration="250">
    <RouterView />
  </TooltipProvider>
</template>
