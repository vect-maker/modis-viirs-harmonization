<script setup lang="ts">
import { TooltipProvider } from 'reka-ui'
import { RouterView, useRoute } from 'vue-router'
import NotificationToasts from '@/components/common/NotificationToasts.vue'
import { useNotificationStream } from '@/composables/useNotificationStream'

useNotificationStream()
// La landing es pública: los avisos del stream de alertas solo tienen sentido en la app.
const route = useRoute()
</script>

<template>
  <TooltipProvider :delay-duration="250">
    <RouterView />
    <NotificationToasts v-if="route.name !== 'landing'" />
  </TooltipProvider>
</template>
