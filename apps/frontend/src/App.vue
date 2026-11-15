<script setup lang="ts">
import { TooltipProvider } from 'reka-ui'
import { RouterView } from 'vue-router'
import NotificationToasts from '@/components/common/NotificationToasts.vue'
import { useNotificationStream } from '@/composables/useNotificationStream'

useNotificationStream()
</script>

<template>
  <TooltipProvider :delay-duration="250">
    <RouterView />
    <NotificationToasts />
  </TooltipProvider>
</template>
