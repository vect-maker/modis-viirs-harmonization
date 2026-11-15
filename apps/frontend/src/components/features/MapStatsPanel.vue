<script setup lang="ts">
import { computed, nextTick, shallowRef, useId, useTemplateRef, watch } from 'vue'
import { onKeyStroke } from '@vueuse/core'
import { storeToRefs } from 'pinia'
import { ChartColumn, ChevronDown } from '@lucide/vue'
import { useHotspotsStore } from '@/stores/hotspots'
import BaseToggleGroup from '@/components/ui/BaseToggleGroup.vue'
import AnnualActivityPanel from './AnnualActivityPanel.vue'
import MonthlyComparisonPanel from './MonthlyComparisonPanel.vue'

defineProps<{
  /** Id del contenedor del mapa donde se dibuja el panel expandido. */
  stageId: string
}>()

// Dos raíces (tarjeta + Teleport): los atributos del padre van a la tarjeta.
defineOptions({ inheritAttrs: false })

const open = defineModel<boolean>('open', { required: true })
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

type Metric = 'raw' | 'harmonized'
type AreaScope = 'area' | 'all'

const METRIC_OPTIONS = [
  { value: 'raw', label: 'Detections' },
  { value: 'harmonized', label: 'Harmonized index' },
] as const satisfies readonly { value: Metric; label: string }[]

const AREA_OPTIONS = [
  { value: 'area', label: 'Drawn area' },
  { value: 'all', label: 'All regions' },
] as const satisfies readonly { value: AreaScope; label: string }[]

// Métrica y área se comparten entre todos los gráficos para que muestren lo mismo.
const { selectedPolygon } = storeToRefs(useHotspotsStore())
const metric = shallowRef<Metric>('raw')
const areaScope = shallowRef<AreaScope>(selectedPolygon.value ? 'area' : 'all')
const activePolygon = computed(() =>
  areaScope.value === 'area' ? selectedPolygon.value : null,
)
watch(selectedPolygon, (polygon) => {
  areaScope.value = polygon ? 'area' : 'all'
})

const metricHelp = computed(() =>
  metric.value === 'harmonized'
    ? 'Harmonized index weights MODIS detections so years before and after the 2012 VIIRS launch can be compared on one scale. Experimental index, not a fire count.'
    : 'Raw MODIS and VIIRS detections. VIIRS adds many small fires from 2012 on, so earlier years read low on this scale.',
)
const areaHelp = computed(() =>
  selectedPolygon.value
    ? ''
    : 'Showing all regions. To compare a specific place, collapse this panel and draw an area on the map.',
)

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
      aria-label="Expand statistics"
      @click="open = true"
    >
      <ChartColumn aria-hidden="true" class="h-4 w-4 text-accent" />
      <span class="flex-1 text-sm font-semibold">Statistics</span>
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
          aria-label="Collapse statistics"
          @click="open = false"
        >
          <ChartColumn aria-hidden="true" class="h-4 w-4 text-accent" />
          <span :id="titleId" class="flex-1 text-sm font-semibold">Statistics</span>
          <span class="hidden text-xs text-ink-muted sm:inline">Esc to close</span>
          <ChevronDown aria-hidden="true" class="h-4 w-4 rotate-180 text-ink-muted" />
        </button>
        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          <div
            class="flex flex-wrap items-center gap-x-5 gap-y-3 border-b border-border-subtle px-5 py-4"
          >
            <BaseToggleGroup v-model="metric" :options="METRIC_OPTIONS" label="Metric" />
            <BaseToggleGroup
              v-if="selectedPolygon"
              v-model="areaScope"
              :options="AREA_OPTIONS"
              label="Area"
            />
            <p class="min-w-0 flex-1 basis-80 text-xs leading-relaxed text-ink-muted">
              {{ metricHelp }} {{ areaHelp }}
            </p>
          </div>
          <MonthlyComparisonPanel :metric="metric" :polygon="activePolygon" />
          <AnnualActivityPanel
            :metric="metric"
            :polygon="activePolygon"
            class="border-t border-border-subtle"
          />
        </div>
      </section>
    </Transition>
  </Teleport>
</template>
