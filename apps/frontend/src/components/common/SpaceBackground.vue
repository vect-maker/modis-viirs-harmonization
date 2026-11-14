<script setup lang="ts">
import { computed, useTemplateRef, watch } from 'vue'
import { useDocumentVisibility, useRafFn, useResizeObserver } from '@vueuse/core'
import {
  createSpaceStars,
  paintSpaceDust,
  paintSpaceStars,
  paintSpaceMeteor,
} from '@/utils/spaceScene'
import type { SpaceStar, SpaceMeteor } from '@/utils/spaceScene'

const props = defineProps<{ visible: boolean }>()
const canvas = useTemplateRef<HTMLCanvasElement>('canvas')
const visibility = useDocumentVisibility()
// Run decorative effects only while the globe and its tab are visible.
const playing = computed(() => props.visible && visibility.value === 'visible')

let context: CanvasRenderingContext2D | null = null
let backdrop: HTMLCanvasElement | null = null
let stars: SpaceStar[] = []
let width = 0
let height = 0
let time = 0
let nextMeteorAt = 6
let meteor: SpaceMeteor | null = null

function paint() {
  if (!context || !backdrop || !width || !height) return
  context.clearRect(0, 0, width, height)
  context.drawImage(backdrop, 0, 0, width, height)
  paintSpaceStars(context, stars, width, height, time)
  if (meteor) paintSpaceMeteor(context, meteor, width, height, time)
}

function resize() {
  const element = canvas.value
  if (!element) return
  const bounds = element.getBoundingClientRect()
  width = Math.round(bounds.width)
  height = Math.round(bounds.height)
  if (!width || !height) return
  const ratio = Math.min(window.devicePixelRatio || 1, 1.5)
  element.width = Math.round(width * ratio)
  element.height = Math.round(height * ratio)
  context = element.getContext('2d')
  context?.setTransform(ratio, 0, 0, ratio, 0, 0)
  backdrop = document.createElement('canvas')
  backdrop.width = element.width
  backdrop.height = element.height
  const backgroundContext = backdrop.getContext('2d')
  if (backgroundContext) {
    backgroundContext.setTransform(ratio, 0, 0, ratio, 0, 0)
    paintSpaceDust(backgroundContext, width, height)
  }
  stars = createSpaceStars(width, height)
  paint()
}

const { pause, resume } = useRafFn(
  ({ delta }) => {
    // Advance only while visible; never replay missed events after returning to the tab.
    time += Math.min(delta, 100) / 1000
    if (meteor && time >= meteor.start + meteor.duration) meteor = null
    if (time >= nextMeteorAt) {
      meteor = {
        start: time,
        duration: 1.5 + Math.random() * 0.5,
        x: Math.random() * 0.65,
        y: Math.random() * 0.45,
        distance: Math.min(750, Math.max(250, width * 0.55)),
        angle: 0.35 + Math.random() * 0.25,
      }
      nextMeteorAt = time + 15 + Math.random() * 10
    }
    paint()
  },
  { immediate: false, fpsLimit: 30 },
)

watch(
  playing,
  (active) => {
    if (active) resume()
    else {
      pause()
      meteor = null
      paint()
    }
  },
  { immediate: true },
)

useResizeObserver(canvas, resize)
</script>

<template>
  <canvas
    ref="canvas"
    class="space-background"
    :class="{ 'space-background-hidden': !visible }"
    aria-hidden="true"
  />
</template>

<style scoped>
.space-background {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  opacity: 1;
  transition: opacity 600ms ease;
}
.space-background-hidden {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .space-background {
    transition: none;
  }
}
</style>
