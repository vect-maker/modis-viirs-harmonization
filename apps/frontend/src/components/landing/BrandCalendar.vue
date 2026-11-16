<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { ArrowUpRight, ChevronLeft, ChevronRight, Info } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useLocaleFormatters } from '@/i18n'
import { useCalendarStore } from '@/stores/calendar'
import type { CalendarCell, CalendarSensor } from '@/types/calendar'
import { calendarCount } from '@/utils/historicalCalendar'
import { getThermalPalette } from '@/utils/themeColors'

const BurningCalendar = defineAsyncComponent(
  () => import('@/components/common/BurningCalendar.vue'),
)

const calendarStore = useCalendarStore()
const { archive, isLoading, hasLoaded, error } = storeToRefs(calendarStore)
onMounted(() => {
  void calendarStore.fetchHistoricalCalendar()
})

const { t } = useI18n()
const { bcp47Locale, formatInt } = useLocaleFormatters()
const year = shallowRef(2024)
const month = shallowRef(5)
const sensor = shallowRef<CalendarSensor>('ALL')
const shortMonthFmt = computed(
  () => new Intl.DateTimeFormat(bcp47Locale.value, { month: 'short', timeZone: 'UTC' }),
)
const longMonthFmt = computed(
  () => new Intl.DateTimeFormat(bcp47Locale.value, { month: 'long', timeZone: 'UTC' }),
)
const labels = computed(() =>
  Array.from({ length: 12 }, (_, i) => shortMonthFmt.value.format(new Date(Date.UTC(2024, i, 1)))),
)
const fullLabels = computed(() =>
  Array.from({ length: 12 }, (_, i) => longMonthFmt.value.format(new Date(Date.UTC(2024, i, 1)))),
)
const firstYear = computed(() =>
  archive.value.firstDetection ? Number(archive.value.firstDetection.slice(0, 4)) : 2020,
)
// Latest complete 12-month archive year, excluding partial/NRT current-year data.
const lastYear = computed(() => {
  const monthsPerYear = new Map<number, number>()
  for (const item of archive.value.months) {
    monthsPerYear.set(item.year, (monthsPerYear.get(item.year) ?? 0) + 1)
  }
  const complete = [...monthsPerYear].filter(([, n]) => n === 12).map(([y]) => y)
  return complete.length > 0 ? Math.max(...complete) : 2025
})
const isReady = computed(() => hasLoaded.value && archive.value.months.length > 0)
const years = computed(() =>
  Array.from({ length: lastYear.value - firstYear.value + 1 }, (_, i) => lastYear.value - i),
)
const recentYears = computed(() =>
  Array.from({ length: 6 }, (_, i) => lastYear.value - 5 + i),
)
const index = computed(
  () => new Map(archive.value.months.map((item) => [`${item.year}-${item.month}`, item])),
)
const maximum = computed(() =>
  Math.max(
    1,
    ...archive.value.months
      .filter((item) => item.year <= lastYear.value)
      .map((item) => calendarCount(item, sensor.value) ?? 0),
  ),
)
const rows = computed(() =>
  recentYears.value.map((y) => ({
    year: y,
    cells: labels.value.map((_, i): CalendarCell => {
      const m = i + 1
      const item = index.value.get(`${y}-${m}`)
      return {
        year: y,
        month: m,
        count: calendarCount(item, sensor.value),
      }
    }),
  })),
)
const palette = computed(() => getThermalPalette())
function onSelectPeriod(selectedYear: number, selectedMonth: number) {
  year.value = selectedYear
  month.value = selectedMonth
}
const selected = computed(() => index.value.get(`${year.value}-${month.value}`))
const selectedCount = computed(() => calendarCount(selected.value, sensor.value))
const yearCells = computed(() =>
  labels.value.map((label, i) => ({
    label,
    month: i + 1,
    count: calendarCount(index.value.get(`${year.value}-${i + 1}`), sensor.value),
  })),
)
const peakMonth = computed(() =>
  yearCells.value.reduce(
    (best, cell) => ((cell.count ?? -1) > (best.count ?? -1) ? cell : best),
    yearCells.value[0]!,
  ),
)
</script>

<template>
  <section id="datos" class="landing-section landing-data-section" aria-labelledby="calendar-title">
    <div class="landing-wrap">
      <div class="landing-section-heading">
        <h2 id="calendar-title">
          {{ t('landing.calendar.titleLine1') }}<br />{{ t('landing.calendar.titleLine2') }}
        </h2>
        <p>
          {{ t('landing.calendar.subtitle') }}
        </p>
      </div>
      <div class="landing-calendar-layout">
        <div class="landing-calendar-frame">
          <div class="landing-calendar-frame-head">
            <div>
              <h3>{{ t('landing.calendar.monthlyActivity') }}</h3>
              <span class="landing-calendar-scope">{{ t('landing.calendar.scope') }}</span>
            </div>
            <span class="landing-source-chip">NASA FIRMS</span>
          </div>
          <p v-if="isLoading && !isReady" class="landing-calendar-state" role="status">
            {{ t('landing.calendar.loading') }}
          </p>
          <div v-else-if="!isReady" class="landing-calendar-state" role="alert">
            <p>{{ t('landing.calendar.error') }}</p>
            <button
              v-if="error"
              type="button"
              class="landing-text-link"
              @click="calendarStore.fetchHistoricalCalendar()"
            >
              {{ t('common.retry') }}
            </button>
          </div>
          <div v-else class="landing-calendar-matrix">
            <BurningCalendar
              :rows="rows"
              :max-count="maximum"
              :selected-period="{ year, month }"
              @select="onSelectPeriod"
            />
          </div>
          <div v-if="isReady" class="landing-calendar-legend">
            <span>{{ t('landing.calendar.fewer') }}</span>
            <div aria-hidden="true">
              <i v-for="color in palette" :key="color" :style="{ backgroundColor: color }" />
            </div>
            <span>{{ t('landing.calendar.more') }}</span>
          </div>
          <div v-if="isReady" class="landing-calendar-controls">
            <div class="landing-year-picker">
              <button
                type="button"
                :disabled="year <= firstYear"
                :aria-label="t('landing.calendar.prevYear')"
                @click="year--"
              >
                <ChevronLeft :size="18" aria-hidden="true" /></button
              ><label
                ><span class="landing-sr-only">{{ t('landing.calendar.yearLabel') }}</span
                ><select v-model="year">
                  <option v-for="option in years" :key="option" :value="option">
                    {{ option }}
                  </option>
                </select></label
              ><button
                type="button"
                :disabled="year >= lastYear"
                :aria-label="t('landing.calendar.nextYear')"
                @click="year++"
              >
                <ChevronRight :size="18" aria-hidden="true" />
              </button>
            </div>
            <label class="landing-calendar-sensor"
              ><span class="landing-sr-only">{{ t('landing.calendar.sensorLabel') }}</span
              ><select v-model="sensor">
                <option value="ALL">{{ t('common.bothSensors') }}</option>
                <option value="MODIS">{{ t('common.modis') }}</option>
                <option value="VIIRS">{{ t('common.viirs') }}</option>
              </select></label
            >
          </div>
          <div
            v-if="isReady"
            class="landing-month-picker"
            role="group"
            :aria-label="t('landing.calendar.monthGroupAria', { year })"
          >
            <button
              v-for="cell in yearCells"
              :key="cell.month"
              type="button"
              :aria-pressed="month === cell.month"
              :aria-label="
                t('landing.calendar.monthAria', {
                  month: fullLabels[cell.month - 1],
                  year,
                  detail:
                    cell.count === null
                      ? t('landing.calendar.monthNoData')
                      : t('landing.calendar.monthDetections', { count: formatInt(cell.count) }),
                })
              "
              @click="month = cell.month"
            >
              {{ cell.label }}
            </button>
          </div>
        </div>
        <div class="landing-calendar-insight">
          <div
            v-if="isReady"
            class="landing-calendar-result"
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            <p class="landing-result-period">{{ fullLabels[month - 1] }} {{ year }}</p>
            <strong>{{ selectedCount === null ? '—' : formatInt(selectedCount) }}</strong>
            <p>
              {{
                selectedCount === null
                  ? t('landing.calendar.noDataForPeriod')
                  : t('landing.calendar.recorded')
              }}
            </p>
          </div>
          <div v-if="isReady" class="landing-peak-note">
            <span>{{ t('landing.calendar.peakInYear', { year }) }}</span
            ><strong>{{
              (peakMonth.count ?? 0) > 0 ? fullLabels[peakMonth.month - 1] : t('common.noData')
            }}</strong>
          </div>
          <div class="landing-science-note">
            <Info :size="18" aria-hidden="true" />
            <p>
              {{ t('landing.calendar.scienceNote') }}
            </p>
          </div>
          <RouterLink :to="{ name: 'dashboard' }" class="landing-text-link"
            >{{ t('landing.calendar.openExplorer') }} <ArrowUpRight :size="17" aria-hidden="true"
          /></RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>
