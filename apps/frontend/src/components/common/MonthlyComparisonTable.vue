<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocaleFormatters } from '@/i18n'
import {
  monthStatus,
  type ComparisonMetric,
  type ComparisonMonth,
  type MonthStatus,
} from './MonthlyComparisonChart.vue'

const { t } = useI18n()
const { bcp47Locale } = useLocaleFormatters()

const props = defineProps<{
  months: readonly ComparisonMonth[]
  year: number
  metric: ComparisonMetric
  valueLabel: string
  fractionDigits: number
}>()

const monthFormatter = computed(
  () => new Intl.DateTimeFormat(bcp47Locale.value, { month: 'short', timeZone: 'UTC' }),
)
const localizedMonths = computed(() =>
  Array.from({ length: 12 }, (_, i) => monthFormatter.value.format(new Date(Date.UTC(2024, i, 1)))),
)

const valueFormat = computed(
  () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: props.fractionDigits }),
)
const pctFormat = computed(
  () =>
    new Intl.NumberFormat(bcp47Locale.value, {
      maximumFractionDigits: 0,
      signDisplay: 'exceptZero',
    }),
)

const STATUS_SHORT_KEY: Record<MonthStatus, string> = {
  above: 'aboveShort',
  typical: 'typicalShort',
  below: 'belowShort',
  partial: 'partialShort',
  unharmonized: 'unharmonizedShort',
  insufficient: 'insufficientShort',
  missing: 'missingShort',
}

const STATUS_CLASS: Record<MonthStatus, string> = {
  above: 'text-accent-bright',
  typical: 'text-ink-secondary',
  below: 'text-sky-300',
  partial: 'text-ink-muted',
  unharmonized: 'text-ink-muted',
  insufficient: 'text-ink-muted',
  missing: 'text-ink-muted',
}

function format(value: number | null): string {
  return value === null ? '' : valueFormat.value.format(value)
}

const rows = computed(() =>
  props.months.map((month, index) => {
    const status = monthStatus(month, props.metric)
    const { p25, p75, median } = month.historic
    const statusLabel = t(`charts.monthly.status.${STATUS_SHORT_KEY[status]}`)
    return {
      key: month.month,
      label: localizedMonths.value[index],
      value: format(month.year_count),
      median: format(median),
      range:
        p25 === null || p75 === null
          ? ''
          : t('charts.monthly.rangeTo', { low: format(p25), high: format(p75) }),
      change:
        month.anomaly_pct_median === null || month.year_count === null
          ? ''
          : `${pctFormat.value.format(month.anomaly_pct_median)}%`,
      status: month.provisional
        ? `${statusLabel}${t('charts.monthly.status.nearRealTimeSuffix')}`
        : statusLabel,
      statusClass: STATUS_CLASS[status],
    }
  }),
)
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full min-w-[34rem] text-left text-xs tabular-nums">
      <caption class="sr-only">
        {{ t('charts.monthly.tableCaption', { label: valueLabel, year }) }}
      </caption>
      <thead class="text-ink-muted">
        <tr class="border-b border-border-subtle">
          <th scope="col" class="py-2 pr-4 font-medium">{{ t('charts.monthly.colMonth') }}</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">{{ year }}</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">{{ t('charts.monthly.colMedian') }}</th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">
            {{ t('charts.monthly.colTypicalRange') }}
          </th>
          <th scope="col" class="py-2 pr-4 text-right font-medium">
            {{ t('charts.monthly.colVsMedian') }}
          </th>
          <th scope="col" class="py-2 font-medium">{{ t('charts.monthly.colStatus') }}</th>
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
