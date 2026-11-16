<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocaleFormatters } from '@/i18n'
import {
  annualValue,
  completeYearMedian,
  type AnnualMetric,
  type AnnualRow,
} from './AnnualActivityChart.vue'

const { t } = useI18n()
const { bcp47Locale } = useLocaleFormatters()

const props = defineProps<{
  rows: readonly AnnualRow[]
  metric: AnnualMetric
}>()

const countFormat = computed(
  () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 0 }),
)
const indexFormat = computed(
  () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 1 }),
)
const pctFormat = computed(
  () =>
    new Intl.NumberFormat(bcp47Locale.value, {
      maximumFractionDigits: 0,
      signDisplay: 'exceptZero',
    }),
)

const tableRows = computed(() => {
  const median = completeYearMedian(props.rows, props.metric)
  return [...props.rows].reverse().map((row) => {
    const value = annualValue(row, props.metric)
    return {
      year: row.year,
      modis: countFormat.value.format(row.modis_count),
      viirs: countFormat.value.format(row.viirs_count),
      total: countFormat.value.format(row.total_hotspots),
      harmonized: indexFormat.value.format(row.harmonized_index),
      change:
        row.complete && median !== null && median > 0
          ? `${pctFormat.value.format(((value - median) / median) * 100)}%`
          : '',
      coverage: row.complete
        ? t('charts.annual.fullYear')
        : t('charts.annual.monthsCount', { months: row.months_in_archive }),
      complete: row.complete,
    }
  })
})
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full min-w-[38rem] text-left text-xs tabular-nums">
      <caption class="sr-only">
        {{ t('charts.annual.tableCaption') }}
      </caption>
      <thead class="text-ink-muted">
        <tr class="border-b border-border-subtle">
          <th scope="col" class="py-2 pr-4 font-medium">{{ t('charts.annual.colYear') }}</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">{{ t('common.modis') }}</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">{{ t('common.viirs') }}</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">{{ t('charts.annual.colTotal') }}</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">
            {{ t('charts.annual.colHarmonized') }}
          </th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">
            {{ t('charts.annual.colVsMedian') }}
          </th>
          <th scope="col" class="py-2 font-medium">{{ t('charts.annual.colCoverage') }}</th>
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
