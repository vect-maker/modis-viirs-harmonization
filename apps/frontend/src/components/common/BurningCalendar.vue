<script setup lang="ts">
import { computed } from 'vue'
import type { CalendarCell } from '@/types/calendar'
import { calendarColor } from '@/utils/historicalCalendar'
const props = defineProps<{
  rows: { year: number; cells: CalendarCell[] }[]
  maxCount: number
  selectedPeriod: { year: number; month: number } | null
}>()
const emit = defineEmits<{ select: [year: number, month: number] }>()
const formatter = new Intl.DateTimeFormat('en-US', { month: 'short', timeZone: 'UTC' })
const months = Array.from({ length: 12 }, (_, i) =>
  formatter.format(new Date(Date.UTC(2024, i, 1))),
)
const number = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })
const rows = computed(() =>
  props.rows.map((row) => ({
    ...row,
    cells: row.cells.map((cell) => ({
      ...cell,
      label: `${months[cell.month - 1]} ${cell.year}: ${cell.count === null ? 'no records; coverage unverified' : cell.count.toLocaleString() + ' observed detections'}`,
      color: calendarColor(cell.count, props.maxCount),
      selected:
        props.selectedPeriod?.year === cell.year && props.selectedPeriod?.month === cell.month,
    })),
  })),
)
</script>

<template>
  <div
    class="max-h-72 overflow-auto rounded-lg border border-white/10"
    tabindex="0"
    aria-label="Historical monthly detections. Scroll to explore years."
  >
    <table class="w-full min-w-[36rem] border-separate border-spacing-1 text-xs">
      <caption class="sr-only">
        Monthly observed hotspot detections in Nicaragua. Missing records do not indicate zero
        fires.
      </caption>
      <thead class="sticky top-0 z-10 bg-surface-panel">
        <tr>
          <th
            scope="col"
            class="sticky left-0 bg-surface-panel p-2 text-left font-medium text-ink-muted"
          >
            Year
          </th>
          <th
            v-for="month in months"
            :key="month"
            scope="col"
            class="py-2 font-normal text-ink-muted"
          >
            {{ month }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.year">
          <th
            scope="row"
            class="sticky left-0 bg-surface-panel px-2 text-left font-mono font-normal text-ink-secondary"
          >
            {{ row.year }}
          </th>
          <td v-for="cell in row.cells" :key="cell.month" class="p-0">
            <button
              type="button"
              class="calendar-cell"
              :class="{
                'calendar-cell-missing': cell.count === null,
                'calendar-cell-selected': cell.selected,
              }"
              :style="{ backgroundColor: cell.color }"
              :aria-label="cell.label"
              :title="cell.label"
              :aria-pressed="cell.selected"
              @click="emit('select', cell.year, cell.month)"
            >
              {{ cell.count === null ? '—' : number.format(cell.count) }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.calendar-cell {
  display: block;
  width: 100%;
  min-height: 30px;
  border-radius: 4px;
  color: #ffedd5;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
}
.calendar-cell:hover {
  outline: 1px solid #ffffff80;
  outline-offset: -1px;
}
.calendar-cell:focus-visible {
  outline: 2px solid white;
  outline-offset: -2px;
}
.calendar-cell-selected {
  box-shadow: inset 0 0 0 2px white;
}
.calendar-cell-missing {
  color: #65717a;
  background-image: repeating-linear-gradient(135deg, #ffffff06 0 3px, transparent 3px 6px);
}
</style>
