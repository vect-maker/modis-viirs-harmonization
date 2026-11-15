<script setup lang="ts">
import { computed } from 'vue'
import {
  annualValue,
  completeYearMedian,
  type AnnualMetric,
  type AnnualRow,
} from './AnnualActivityChart.vue'

const props = defineProps<{
  rows: readonly AnnualRow[]
  metric: AnnualMetric
}>()

const countFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const indexFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })
const pctFormat = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0,
  signDisplay: 'exceptZero',
})

const tableRows = computed(() => {
  const median = completeYearMedian(props.rows, props.metric)
  return [...props.rows].reverse().map((row) => {
    const value = annualValue(row, props.metric)
    return {
      year: row.year,
      modis: countFormat.format(row.modis_count),
      viirs: countFormat.format(row.viirs_count),
      total: countFormat.format(row.total_hotspots),
      harmonized: indexFormat.format(row.harmonized_index),
      change:
        row.complete && median !== null && median > 0
          ? `${pctFormat.format(((value - median) / median) * 100)}%`
          : '',
      coverage: row.complete ? 'Full year' : `${row.months_in_archive} of 12 months`,
      complete: row.complete,
    }
  })
})
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full min-w-[38rem] text-left text-xs tabular-nums">
      <caption class="sr-only">
        Detections per year by sensor and harmonized index
      </caption>
      <thead class="text-ink-muted">
        <tr class="border-b border-border-subtle">
          <th scope="col" class="py-2 pr-4 font-medium">Year</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">MODIS</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">VIIRS</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">Total</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">Harmonized index</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">vs. median year</th>
          <th scope="col" class="py-2 font-medium">Archive coverage</th>
        </tr>
      </thead>
      <tbody class="text-ink-secondary">
        <tr
          v-for="row in tableRows"
          :key="row.year"
          class="border-b border-border-subtle/60 last:border-0"
        >
          <th scope="row" class="py-2 pr-4 font-medium text-ink-primary">{{ row.year }}</th>
          <td class="py-2 pr-4 text-right">{{ row.modis }}</td>
          <td class="py-2 pr-4 text-right">{{ row.viirs }}</td>
          <td class="py-2 pr-4 text-right">{{ row.total }}</td>
          <td class="py-2 pr-4 text-right">{{ row.harmonized }}</td>
          <td class="py-2 pr-4 text-right">{{ row.change }}</td>
          <td class="py-2" :class="row.complete ? 'text-ink-secondary' : 'text-ink-muted'">
            {{ row.coverage }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
