<script setup lang="ts">
import { shallowRef, useTemplateRef, watch } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'

const props = defineProps<{
  eager?: boolean
}>()

const container = useTemplateRef<HTMLDivElement>('container')
const hasEntered = shallowRef(Boolean(props.eager))

watch(
  () => props.eager,
  (isEager) => {
    if (isEager) hasEntered.value = true
  },
)

const { stop } = useIntersectionObserver(
  container,
  (entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      hasEntered.value = true
      stop()
    }
  },
  { rootMargin: '280px' },
)
</script>

<template>
  <div ref="container">
    <slot v-if="hasEntered" />
    <div v-else class="p-5" aria-hidden="true">
      <div class="h-[20rem] rounded-lg bg-white/[0.03] motion-safe:animate-pulse" />
    </div>
  </div>
</template>
