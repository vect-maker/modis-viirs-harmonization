<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { ChartColumn, MapPin } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useLocaleFormatters } from '@/i18n'
import { useCalendarStore } from '@/stores/calendar'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseSensorFilter from '@/components/ui/BaseSensorFilter.vue'
import BurningCalendar from '@/components/common/BurningCalendar.vue'
import { getThermalPalette } from '@/utils/themeColors'

const emit = defineEmits<{
  'load-month': []
  'compare-year': [year: number]
}>()

const { t } = useI18n()
const { bcp47Locale, formatInt } = useLocaleFormatters()
const store = useCalendarStore()
const hotspotsStore = useHotspotsStore()
const { archive, sensor, rows, maxCount, total, selectedPeriod, selectedMonth, selectedCount } =
  storeToRefs(store)
const { isLoading: isMapLoading, dateRange: mapDateRange } = storeToRefs(hotspotsStore)

onMounted(() => {
  void store.fetchHistoricalCalendar()
})
const dateFormatter = computed(
  () =>
    new Intl.DateTimeFormat(bcp47Locale.value, {
      month: 'long',
      year: 'numeric',
      timeZone: 'UTC',
    }),
)
const selectedLabel = computed(() =>
  selectedPeriod.value
    ? dateFormatter.value.format(
        new Date(Date.UTC(selectedPeriod.value.year, selectedPeriod.value.month - 1, 1)),
      )
    : '',
)
const palette = computed(() => getThermalPalette())
function formatCount(value: number | null | undefined) {
  return value == null ? t('common.noRecords') : formatInt(value)
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
  <section class="space-y-3 p-3 sm:p-5" :aria-label="t('stats.archive.aria')">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-medium">
          {{ t('stats.archive.title') }}<template v-if="archive.firstDetection && archive.lastDetection">
            · {{ archive.firstDetection.slice(0, 4) }}–{{ archive.lastDetection.slice(0, 4) }}
          </template>
        </h2>
        <p class="mt-1 text-xs text-ink-muted">
          {{ t('stats.archive.subtitle', { total: formatInt(total) }) }}
        </p>
      </div>
      <BaseSensorFilter
        :model-value="sensor"
        class="w-full sm:w-60"
        @update:model-value="store.setSensor"
      />
    </div>
    <p class="text-[11px] leading-relaxed text-ink-muted">
      {{ t('stats.archive.disclaimer') }}
    </p>
    <BurningCalendar
      :rows="rows"
      :max-count="maxCount"
      :selected-period="selectedPeriod"
      @select="store.selectMonth"
    />
    <div class="flex flex-wrap items-center gap-3 text-[10px] text-ink-muted">
      <span class="inline-flex items-center gap-1.5"
        ><span class="calendar-unknown h-3 w-4 rounded-sm border border-border-subtle" />{{
          t('stats.archive.noRecordsCoverage')
        }}</span
      >
      <span class="ml-auto inline-flex items-center gap-1"
        >{{ t('stats.archive.low') }}
        <span
          v-for="color in palette"
          :key="color"
          class="h-3 w-4 rounded-sm"
          :style="{ backgroundColor: color }"
        />
        {{ t('stats.archive.high') }}</span
      >
      <span>{{ t('stats.archive.logScale', { max: formatInt(maxCount) }) }}</span>
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
          }}<span v-if="selectedCount !== null" class="ml-1 font-sans text-xs text-ink-muted">{{
            t('stats.archive.detectionsSensor', {
              sensor: sensor === 'ALL' ? t('stats.archive.allSensors') : sensor,
            })
          }}</span>
        </p>
      </div>
      <p class="text-xs text-ink-secondary">
        MODIS: {{ formatCount(selectedMonth?.modisCount) }} · VIIRS:
        {{ formatCount(selectedMonth?.viirsCount) }}
      </p>
      <p v-if="selectedMonth" class="text-[11px] text-ink-muted">
        {{ t('stats.archive.observedDays', { days: selectedMonth.observedDays }) }}
      </p>
      <p v-else class="text-xs text-ink-muted">
        {{ t('stats.archive.noMonthRecords') }}
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
              ? t('stats.archive.loadingMonth')
              : isMonthLoadedOnMap
                ? t('stats.archive.reloadMonth')
                : t('stats.archive.loadMonth')
          }}
        </button>
        <button
          type="button"
          class="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-border-strong bg-surface-elevated px-3 py-1.5 text-xs font-medium text-ink-primary transition hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-focus"
          @click="compareSelectedYear"
        >
          <ChartColumn aria-hidden="true" class="h-3.5 w-3.5 text-accent" />
          {{ t('stats.archive.compareYear', { year: selectedPeriod.year }) }}
        </button>
      </div>
      <p v-if="selectedMonth && exceedsLargeFetchThreshold" class="text-[11px] text-ink-muted">
        {{ t('stats.archive.largeWarning') }}
      </p>
    </div>
    <p v-else class="text-xs text-ink-muted">
      {{ t('stats.archive.selectMonthPrompt') }}
    </p>
  </section>
</template>

<style scoped>
.calendar-unknown {
  background-image: repeating-linear-gradient(135deg, #ffffff12 0 3px, transparent 3px 6px);
}
</style>
