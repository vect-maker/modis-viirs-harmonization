<script setup lang="ts">
import { computed } from 'vue'
import { parseDate } from '@internationalized/date'
import type { DailyHotspotActivity } from '@/types/hotspot'
import type { HotspotDateRange } from '@/types/filters'

const props = defineProps<{
  days: DailyHotspotActivity[]
  selectedRange: HotspotDateRange | null
}>()
const emit = defineEmits<{ select: [date: string] }>()
const formatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
})
const maxCount = computed(() => Math.max(1, ...props.days.map((day) => day.count)))
const bars = computed(() =>
  props.days.map((day) => ({
    ...day,
    label: formatter.format(parseDate(day.date).toDate('UTC')),
    height: (day.count / maxCount.value) * 90,
    selected:
      !!props.selectedRange &&
      day.date >= props.selectedRange.start &&
      day.date <= props.selectedRange.end,
  })),
)
</script>

<template>
  <div v-if="days.length" class="flex gap-2">
    <div
      aria-hidden="true"
      class="flex w-10 shrink-0 flex-col justify-between pb-7 pt-5 text-right font-mono text-[10px] text-neutral-500"
    >
      <span>{{ maxCount.toLocaleString() }}</span
      ><span>0</span>
    </div>
    <div
      class="min-w-0 flex-1 overflow-x-auto pb-1"
      role="group"
      aria-label="Daily detections. Select a day to filter the map."
    >
      <div
        class="grid gap-1"
        :style="{ gridTemplateColumns: `repeat(${days.length}, minmax(2.5rem, 1fr))` }"
      >
        <button
          v-for="bar in bars"
          :key="bar.date"
          type="button"
          class="group flex min-w-0 flex-col items-center rounded-md px-0.5 py-1 hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-red-400"
          :class="bar.selected && 'bg-red-500/10 ring-1 ring-inset ring-red-500/25'"
          :aria-pressed="bar.selected"
          :aria-label="`${bar.date}: ${bar.count.toLocaleString()} detections. Select this day.`"
          :title="`${bar.label}: ${bar.count.toLocaleString()} detections`"
          @click="emit('select', bar.date)"
        >
          <span class="h-4 font-mono text-[10px] tabular-nums text-neutral-400">{{
            bar.count.toLocaleString()
          }}</span>
          <svg
            aria-hidden="true"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            class="h-24 w-full overflow-visible border-b border-white/10"
          >
            <rect
              x="22"
              :y="100 - bar.height"
              width="56"
              :height="bar.height"
              rx="3"
              class="group-hover:fill-red-300"
              :fill="selectedRange && !bar.selected ? '#7f1d1d' : '#ef4444'"
            />
          </svg>
          <span class="mt-1.5 whitespace-nowrap text-[10px] text-neutral-400">{{ bar.label }}</span>
        </button>
      </div>
    </div>
  </div>
  <p v-else role="status" class="py-5 text-center text-sm text-neutral-400">
    No dated records are available.
  </p>
</template>
