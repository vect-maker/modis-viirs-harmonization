<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { ChartColumn, MapPin } from '@lucide/vue'
import { useCalendarStore } from '@/stores/calendar'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseSensorFilter from '@/components/ui/BaseSensorFilter.vue'
import BurningCalendar from '@/components/common/BurningCalendar.vue'
import { getThermalPalette } from '@/utils/themeColors'

const emit = defineEmits<{
  'load-month': []
  'compare-year': [year: number]
}>()

const store = useCalendarStore()
const hotspotsStore = useHotspotsStore()
const { archive, sensor, rows, maxCount, total, selectedPeriod, selectedMonth, selectedCount } =
  storeToRefs(store)
const { isLoading: isMapLoading, dateRange: mapDateRange } = storeToRefs(hotspotsStore)

onMounted(() => {
  void store.fetchHistoricalCalendar()
})
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

const selectedMonthRange = computed(() => {
  const period = selectedPeriod.value
  if (!period) return null
  const monthStr = String(period.month).padStart(2, '0')
  const lastDay = new Date(Date.UTC(period.year, period.month, 0)).getUTCDate()
  return {
    start: `${period.year}-${monthStr}-01`,
    end: `${period.year}-${monthStr}-${String(lastDay).padStart(2, '0')}`,
  }
})

const isMonthLoadedOnMap = computed(
  () =>
    selectedMonthRange.value !== null &&
    mapDateRange.value?.start === selectedMonthRange.value.start &&
    mapDateRange.value?.end === selectedMonthRange.value.end,
)

const exceedsLargeFetchThreshold = computed(() => (selectedCount.value ?? 0) > 1000)

async function loadSelectedMonthOnMap() {
  if (!selectedMonthRange.value || !selectedMonth.value || isMapLoading.value) return
  hotspotsStore.setSensor(sensor.value)
  await hotspotsStore.selectDateRange(selectedMonthRange.value)
  emit('load-month')
}

function compareSelectedYear() {
  if (!selectedPeriod.value) return
  emit('compare-year', selectedPeriod.value.year)
}
</script>

<template>
  <section class="space-y-3 p-3 sm:p-5" aria-label="Historical burning activity calendar">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-medium">
          Historical Archive<template v-if="archive.firstDetection && archive.lastDetection">
            · {{ archive.firstDetection.slice(0, 4) }}–{{ archive.lastDetection.slice(0, 4) }}
          </template>
        </h2>
        <p class="mt-1 text-xs text-ink-muted">
          {{ total.toLocaleString() }} observed detections · full archive
        </p>
      </div>
      <BaseSensorFilter
        :model-value="sensor"
        class="w-full sm:w-60"
        @update:model-value="store.setSensor"
      />
    </div>
    <p class="text-[11px] leading-relaxed text-ink-muted">
      Archive totals. Map area and date filters do not apply here. Counts are not harmonized;
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
      <div class="flex flex-wrap items-center gap-2 pt-1">
        <button
          v-if="selectedMonth"
          type="button"
          :disabled="isMapLoading || (selectedCount ?? 0) === 0"
          class="inline-flex cursor-pointer items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-surface-base transition hover:brightness-110 focus-visible:outline-2 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-50"
          @click="loadSelectedMonthOnMap"
        >
          <MapPin aria-hidden="true" class="h-3.5 w-3.5" />
          {{
            isMapLoading
              ? 'Loading month...'
              : isMonthLoadedOnMap
                ? 'Reload month on map'
                : 'Load month on map'
          }}
        </button>
        <button
          type="button"
          class="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-border-strong bg-surface-elevated px-3 py-1.5 text-xs font-medium text-ink-primary transition hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-focus"
          @click="compareSelectedYear"
        >
          <ChartColumn aria-hidden="true" class="h-3.5 w-3.5 text-accent" />
          Compare {{ selectedPeriod.year }} in Statistics
        </button>
      </div>
      <p v-if="selectedMonth && exceedsLargeFetchThreshold" class="text-[11px] text-ink-muted">
        More than 1,000 detections in this month — you will be asked to confirm before downloading
        all batches.
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
