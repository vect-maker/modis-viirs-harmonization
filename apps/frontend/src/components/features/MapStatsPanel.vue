<script setup lang="ts">
import { computed, nextTick, shallowRef, useId, useTemplateRef, watch } from 'vue'
import { onKeyStroke } from '@vueuse/core'
import { storeToRefs } from 'pinia'
import { ChartColumn, ChevronDown } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useChartFiltersStore, type ChartAreaScope, type ChartMetric } from '@/stores/chartFilters'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseStatsBreadcrumb, {
  STATS_SECTIONS,
  type StatsSectionId,
} from '@/components/ui/BaseStatsBreadcrumb.vue'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import BaseHelpGuidePopover from '@/components/ui/BaseHelpGuidePopover.vue'
import DashboardGuideDiagram from '@/components/common/DashboardGuideDiagram.vue'
import AnnualActivityChart from '@/components/charts/temporal/AnnualActivityChart.vue'
import AnnualDistributionsChart from '@/components/charts/temporal/AnnualDistributionsChart.vue'
import FireCalendarStatsChart from '@/components/charts/temporal/FireCalendarStatsChart.vue'
import HistoricalCalendar from '@/components/features/HistoricalCalendar.vue'
import MonthlyComparisonChart from '@/components/charts/temporal/MonthlyComparisonChart.vue'
import WeatherCorrelationChart from '@/components/charts/models/WeatherCorrelationChart.vue'

defineProps<{
  /** Id del contenedor del mapa donde se dibuja el panel expandido. */
  stageId: string
}>()

// Dos raíces (tarjeta + Teleport): los atributos del padre van a la tarjeta.
defineOptions({ inheritAttrs: false })

const open = defineModel<boolean>('open', { required: true })
const comparisonYear = defineModel<number | null>('year', { default: null })
const panelId = useId()
const titleId = useId()
const expandButton = useTemplateRef<HTMLButtonElement>('expandButton')
const collapseButton = useTemplateRef<HTMLButtonElement>('collapseButton')

watch(open, async (isOpen) => {
  await nextTick()
  if (isOpen) collapseButton.value?.focus()
  else expandButton.value?.focus()
})

onKeyStroke('Escape', (event) => {
  if (!open.value || event.defaultPrevented) return
  // Esc dentro de un menú desplegable (p. ej. el selector de año) solo cierra ese menú.
  if (document.querySelector('[role="listbox"]')) return
  open.value = false
})

const { t } = useI18n()

type Metric = ChartMetric
type AreaScope = ChartAreaScope

const METRIC_OPTIONS = computed(
  () =>
    [
      { value: 'raw', label: t('stats.detections') },
      { value: 'harmonized', label: t('stats.harmonizedIndex') },
    ] as const satisfies readonly { value: Metric; label: string }[],
)

const AREA_OPTIONS = computed(
  () =>
    [
      { value: 'area', label: t('stats.drawnArea') },
      { value: 'all', label: t('stats.allRegions') },
    ] as const satisfies readonly { value: AreaScope; label: string }[],
)

const SECTION_KEY_MAP: Record<StatsSectionId, string> = {
  seasonal: 'seasonal',
  annual: 'annual',
  archive: 'archive',
  'fire-calendar': 'fireCalendar',
  intensity: 'intensity',
  weather: 'weather',
}

const activeSection = shallowRef<StatsSectionId>('seasonal')
const activeSectionDescription = computed(() =>
  t(`stats.sections.${SECTION_KEY_MAP[activeSection.value]}.description`),
)

const { selectedPolygon, dateRange } = storeToRefs(useHotspotsStore())
const chartFiltersStore = useChartFiltersStore()
const { metric, areaScope, selectedYear } = storeToRefs(chartFiltersStore)

const YEAR_OPTIONS = Array.from({ length: 26 }, (_, i) => {
  const y = 2026 - i
  return { value: y, label: String(y) }
})

function resolveInitialYear(startIso: string | undefined): number {
  if (!startIso) return 2025
  const parsed = Number(startIso.slice(0, 4))
  return Number.isInteger(parsed) && parsed >= 2001 && parsed <= 2025 ? parsed : 2025
}

chartFiltersStore.setSelectedYear(resolveInitialYear(dateRange.value?.start))
watch(
  comparisonYear,
  (val) => {
    if (val !== null && val !== selectedYear.value) {
      chartFiltersStore.setSelectedYear(val)
    }
  },
  { immediate: true },
)
watch(selectedYear, (val) => {
  if (comparisonYear.value !== val) {
    comparisonYear.value = val
  }
})
watch(
  () => dateRange.value?.start,
  (startIso) => {
    if (!startIso) return
    const parsed = Number(startIso.slice(0, 4))
    if (Number.isInteger(parsed) && parsed >= 2001 && parsed <= 2026) {
      chartFiltersStore.setSelectedYear(parsed)
    }
  },
)

const supportsAreaFilter = computed(() => true)

const showMetricToggle = computed(
  () => activeSection.value !== 'weather' && activeSection.value !== 'archive',
)
const showGlobalFilters = computed(() => activeSection.value !== 'archive')

function onCompareYearFromArchive(year: number) {
  chartFiltersStore.setSelectedYear(year)
  activeSection.value = 'seasonal'
}

const metricHelp = computed(() =>
  metric.value === 'harmonized' ? t('stats.metricHelpHarmonized') : t('stats.metricHelpRaw'),
)
const areaHelp = computed(() => (selectedPolygon.value ? '' : t('stats.areaHelp')))

const triggerClass =
  'flex min-h-14 w-full cursor-pointer items-center gap-2.5 px-4 py-3 text-left focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-focus'
</script>

<template>
  <div
    v-show="!open"
    v-bind="$attrs"
    class="overflow-hidden rounded-xl border border-border-strong bg-surface-panel/95 text-ink-primary shadow-[0_8px_32px_#0004] backdrop-blur-xl"
  >
    <button
      ref="expandButton"
      type="button"
      :class="triggerClass"
      :aria-expanded="open"
      :aria-controls="panelId"
      :aria-label="t('stats.expandAria')"
      @click="open = true"
    >
      <ChartColumn aria-hidden="true" class="h-4 w-4 text-accent" />
      <span class="flex-1 text-sm font-semibold">{{ t('stats.title') }}</span>
      <ChevronDown aria-hidden="true" class="h-4 w-4 text-ink-muted" />
    </button>
  </div>

  <Teleport :to="`#${stageId}`" defer>
    <Transition
      enter-active-class="transition duration-200 ease-out motion-reduce:transition-none"
      enter-from-class="scale-[0.98] opacity-0"
      leave-active-class="transition duration-150 ease-in motion-reduce:transition-none"
      leave-to-class="scale-[0.98] opacity-0"
    >
      <section
        v-if="open"
        :id="panelId"
        :aria-labelledby="titleId"
        class="absolute inset-3 z-30 flex origin-top-right flex-col overflow-hidden rounded-xl border border-border-strong bg-surface-panel text-ink-primary shadow-[0_12px_40px_#0006] md:inset-5"
      >
        <button
          ref="collapseButton"
          type="button"
          :class="triggerClass"
          class="shrink-0 border-b border-border-subtle"
          :aria-expanded="open"
          :aria-controls="panelId"
          :aria-label="t('stats.collapseAria')"
          @click="open = false"
        >
          <ChartColumn aria-hidden="true" class="h-4 w-4 text-accent" />
          <span :id="titleId" class="flex-1 text-sm font-semibold">{{ t('stats.title') }}</span>
          <BaseHelpGuidePopover
            :title="t('stats.guideTitle')"
            :summary="t('stats.guideSummary')"
            :steps="[t('stats.guideStep1'), t('stats.guideStep2')]"
            side="bottom"
            align="end"
            :aria-label="t('stats.guideAria')"
          >
            <template #graphic>
              <DashboardGuideDiagram variant="stats" />
            </template>
          </BaseHelpGuidePopover>
          <span class="hidden text-xs text-ink-muted sm:inline">{{ t('stats.escToClose') }}</span>
          <ChevronDown aria-hidden="true" class="h-4 w-4 rotate-180 text-ink-muted" />
        </button>

        <BaseStatsBreadcrumb v-model="activeSection" class="shrink-0" />

        <div class="min-h-0 flex-1 divide-y divide-border-subtle overflow-y-auto overscroll-contain">
          <div class="flex flex-wrap items-center gap-x-5 gap-y-3 px-5 py-4">
            <BaseSelect
              v-if="showGlobalFilters"
              v-model="selectedYear"
              :options="YEAR_OPTIONS"
              :label="t('stats.referenceYear')"
            />
            <BaseToggleGroup
              v-if="showMetricToggle"
              v-model="metric"
              :options="METRIC_OPTIONS"
              :label="t('stats.metric')"
            />
            <BaseToggleGroup
              v-if="showGlobalFilters && selectedPolygon && supportsAreaFilter"
              v-model="areaScope"
              :options="AREA_OPTIONS"
              :label="t('stats.area')"
            />
            <p class="min-w-0 flex-1 basis-80 text-xs leading-relaxed text-ink-muted">
              <template v-if="showMetricToggle">
                {{ metricHelp }} {{ areaHelp }}
              </template>
              <template v-else>
                {{ activeSectionDescription }}
              </template>
            </p>
          </div>

          <MonthlyComparisonChart v-if="activeSection === 'seasonal'" />
          <AnnualActivityChart v-else-if="activeSection === 'annual'" />
          <HistoricalCalendar
            v-else-if="activeSection === 'archive'"
            @load-month="open = false"
            @compare-year="onCompareYearFromArchive"
          />
          <FireCalendarStatsChart v-else-if="activeSection === 'fire-calendar'" />
          <AnnualDistributionsChart v-else-if="activeSection === 'intensity'" />
          <WeatherCorrelationChart v-else-if="activeSection === 'weather'" />
        </div>
      </section>
    </Transition>
  </Teleport>
</template>
