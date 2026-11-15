<script setup lang="ts">
import { computed } from 'vue'
import {
  MONTH_LABELS,
  monthStatus,
  type ComparisonMonth,
  type MonthStatus,
} from './MonthlyComparisonChart.vue'

const props = defineProps<{
  months: readonly ComparisonMonth[]
  year: number
  valueLabel: string
  fractionDigits: number
}>()

const valueFormat = computed(
  () => new Intl.NumberFormat('en-US', { maximumFractionDigits: props.fractionDigits }),
)
const pctFormat = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0,
  signDisplay: 'exceptZero',
})

const STATUS_TEXT: Record<MonthStatus, string> = {
  above: 'Above range',
  typical: 'Typical',
  below: 'Below range',
  insufficient: 'Short baseline',
  'no-data': 'No data yet',
}

const STATUS_CLASS: Record<MonthStatus, string> = {
  above: 'text-accent-bright',
  typical: 'text-ink-secondary',
  below: 'text-sky-300',
  insufficient: 'text-ink-muted',
  'no-data': 'text-ink-muted',
}

function format(value: number | null): string {
  return value === null ? '' : valueFormat.value.format(value)
}

const rows = computed(() =>
  props.months.map((month, index) => {
    const status = monthStatus(month)
    const { p25, p75, median } = month.historic
    return {
      key: month.month,
      label: MONTH_LABELS[index],
      value: format(month.year_count),
      median: format(median),
      range: p25 === null || p75 === null ? '' : `${format(p25)} to ${format(p75)}`,
      change:
        month.anomaly_pct_median === null || month.year_count === null
          ? ''
          : `${pctFormat.format(month.anomaly_pct_median)}%`,
      status: STATUS_TEXT[status],
      statusClass: STATUS_CLASS[status],
    }
  }),
)
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full min-w-[34rem] text-left text-xs tabular-nums">
      <caption class="sr-only">
        Monthly {{ valueLabel }} in {{ year }} compared with the historical baseline
      </caption>
      <thead class="text-ink-muted">
        <tr class="border-b border-border-subtle">
          <th scope="col" class="py-2 pr-4 font-medium">Month</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">{{ year }}</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">Median</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">Typical range</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">vs. median</th>
          <th scope="col" class="py-2 font-medium">Status</th>
        </tr>
      </thead>
      <tbody class="text-ink-secondary">
        <tr v-for="row in rows" :key="row.key" class="border-b border-border-subtle/60 last:border-0">
          <th scope="row" class="py-2 pr-4 font-medium text-ink-primary">{{ row.label }}</th>
          <td class="py-2 pr-4 text-right">{{ row.value }}</td>
          <td class="py-2 pr-4 text-right">{{ row.median }}</td>
          <td class="py-2 pr-4 text-right">{{ row.range }}</td>
          <td class="py-2 pr-4 text-right">{{ row.change }}</td>
          <td class="py-2" :class="row.statusClass">{{ row.status }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
