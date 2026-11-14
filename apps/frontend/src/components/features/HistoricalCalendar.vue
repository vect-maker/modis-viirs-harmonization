<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useCalendarStore } from '@/stores/calendar'
import BaseSensorFilter from '@/components/ui/BaseSensorFilter.vue'
import BurningCalendar from '@/components/common/BurningCalendar.vue'
import { getThermalPalette } from '@/utils/themeColors'
const store = useCalendarStore()
const { archive, sensor, rows, maxCount, total, selectedPeriod, selectedMonth, selectedCount } =
  storeToRefs(store)
const dateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
})
const selectedLabel = computed(() =>
  selectedPeriod.value
    ? dateFormatter.format(
        new Date(Date.UTC(selectedPeriod.value.year, selectedPeriod.value.month - 1, 1)),
      )
    : '',
)
const palette = computed(() => getThermalPalette())
function formatCount(value: number | null | undefined) {
  return value == null ? 'No records' : value.toLocaleString()
}
</script>

<template>
  <section class="space-y-3 p-3 sm:p-5" aria-label="Nicaragua historical burning activity calendar">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-medium">
          Nicaragua · {{ archive.firstDetection.slice(0, 4) }}–{{
            archive.lastDetection.slice(0, 4)
          }}
        </h2>
        <p class="mt-1 text-xs text-ink-muted">
          {{ total.toLocaleString() }} observed detections · national archive
        </p>
      </div>
      <BaseSensorFilter
        :model-value="sensor"
        class="w-full sm:w-60"
        @update:model-value="store.setSensor"
      />
    </div>
    <p class="text-[11px] leading-relaxed text-ink-muted">
      National totals. Map area and date filters do not apply here. Counts are not harmonized;
      observation coverage is unverified.
    </p>
    <BurningCalendar
      :rows="rows"
      :max-count="maxCount"
      :selected-period="selectedPeriod"
      @select="store.selectMonth"
    />
    <div class="flex flex-wrap items-center gap-3 text-[10px] text-ink-muted">
      <span class="inline-flex items-center gap-1.5"
        ><span class="calendar-unknown h-3 w-4 rounded-sm border border-border-subtle" />No records /
        coverage unverified</span
      >
      <span class="ml-auto inline-flex items-center gap-1"
        >Low
        <span
          v-for="color in palette"
          :key="color"
          class="h-3 w-4 rounded-sm"
          :style="{ backgroundColor: color }"
        />
        High</span
      >
      <span>Log scale · up to {{ maxCount.toLocaleString() }} / month</span>
    </div>
    <div
      v-if="selectedPeriod"
      role="status"
      class="space-y-2 rounded-lg border border-border-subtle bg-white/[0.025] p-3"
    >
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h3 class="text-sm font-medium">{{ selectedLabel }}</h3>
        <p class="font-mono text-sm text-accent-bright">
          {{ formatCount(selectedCount)
          }}<span v-if="selectedCount !== null" class="ml-1 font-sans text-xs text-ink-muted"
            >detections · {{ sensor === 'ALL' ? 'all sensors' : sensor }}</span
          >
        </p>
      </div>
      <p class="text-xs text-ink-secondary">
        MODIS: {{ formatCount(selectedMonth?.modisCount) }} · VIIRS:
        {{ formatCount(selectedMonth?.viirsCount) }}
      </p>
      <p v-if="selectedMonth" class="text-[11px] text-ink-muted">
        All sensors: records on {{ selectedMonth.observedDays }} days in this month. This does not
        confirm complete satellite coverage.
      </p>
      <p v-else class="text-xs text-ink-muted">
        No records are present for this month. Fire absence cannot be inferred.
      </p>
      <p class="text-[11px] text-ink-muted">
        The map continues to show the daily sample. Historical point loading is not connected yet.
      </p>
    </div>
    <p v-else class="text-xs text-ink-muted">
      Select a month to inspect its totals and sensor sources.
    </p>
  </section>
</template>

<style scoped>
.calendar-unknown {
  background-image: repeating-linear-gradient(135deg, #ffffff12 0 3px, transparent 3px 6px);
}
</style>
