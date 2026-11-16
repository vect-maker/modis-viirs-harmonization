<script setup lang="ts">
import { computed } from 'vue'
import { parseDate } from '@internationalized/date'
import { storeToRefs } from 'pinia'
import { FilterX } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useLocaleFormatters } from '@/i18n'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseTimelinePanel from '@/components/ui/BaseTimelinePanel.vue'
import BaseHelpGuidePopover from '@/components/ui/BaseHelpGuidePopover.vue'
import DashboardGuideDiagram from '@/components/common/DashboardGuideDiagram.vue'
import DailyActivityChart from '@/components/common/DailyActivityChart.vue'

const { t } = useI18n()
const { bcp47Locale, formatInt } = useLocaleFormatters()
const open = defineModel<boolean>('open', { required: true })
const store = useHotspotsStore()
const { dailyActivity, dateRange, fetchedDateRange, contextHotspots } = storeToRefs(store)
const totalDetections = computed(() =>
  dailyActivity.value.reduce((sum, day) => sum + day.count, 0),
)
const summary = computed(() =>
  t('dashboard.timeline.summary', {
    count: formatInt(totalDetections.value),
    days: dailyActivity.value.length,
  }),
)
const formatter = computed(
  () =>
    new Intl.DateTimeFormat(bcp47Locale.value, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone: 'UTC',
    }),
)
const periodLabel = computed(() => {
  const start = fetchedDateRange.value?.start ?? dailyActivity.value[0]?.date
  const end =
    fetchedDateRange.value?.end ?? dailyActivity.value[dailyActivity.value.length - 1]?.date
  if (!start || !end) return ''
  return formatter.value.formatRange(parseDate(start).toDate('UTC'), parseDate(end).toDate('UTC'))
})
function selectDay(date: string) {
  store.setDateRange({ start: date, end: date })
}
</script>

<template>
  <BaseTimelinePanel v-model:open="open" :summary="summary">
    <template #tools><slot name="tools" /></template>
    <div class="space-y-3 px-3 py-4 sm:px-5">
      <div
        class="flex flex-wrap items-center justify-between gap-2 pl-12 text-xs text-neutral-400"
      >
        <p v-if="periodLabel">{{ periodLabel }} · UTC</p>
        <div class="ml-auto flex items-center gap-2">
          <button
            v-if="dateRange"
            type="button"
            class="inline-flex items-center gap-1 rounded text-xs hover:text-white focus-visible:outline-2 focus-visible:outline-red-400"
            @click="store.setDateRange(null)"
          >
            <FilterX aria-hidden="true" class="h-3.5 w-3.5" />{{
              t('dashboard.timeline.showAllDates')
            }}
          </button>
          <BaseHelpGuidePopover
            :title="t('dashboard.timeline.guideTitle')"
            :summary="t('dashboard.timeline.guideSummary')"
            :steps="[
              t('dashboard.timeline.guideStep1'),
              t('dashboard.timeline.guideStep2'),
            ]"
            side="top"
            align="end"
            :aria-label="t('dashboard.timeline.guideAria')"
          >
            <template #graphic>
              <DashboardGuideDiagram variant="timeline" />
            </template>
          </BaseHelpGuidePopover>
        </div>
      </div>
      <DailyActivityChart
        :days="dailyActivity"
        :selected-range="dateRange"
        @select="selectDay"
      />
      <p
        v-if="!contextHotspots.length"
        role="status"
        class="text-center text-xs text-neutral-400"
      >
        {{ t('dashboard.timeline.empty') }}
      </p>
      <p class="pl-12 text-[11px] leading-relaxed text-neutral-400">
        {{ t('dashboard.timeline.coverageNote') }}
      </p>
    </div>
  </BaseTimelinePanel>
</template>
