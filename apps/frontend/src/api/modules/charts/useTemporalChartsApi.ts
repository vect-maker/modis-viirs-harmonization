import { useApiFetch } from '@/api/useApiFetch'
import { useHotspotsApi } from '../hotspots/useHotspotsApi'
import {
  buildChartQueryString,
  type AnnualStatsQuery,
  type FireCalendarQuery,
  type MonthlyComparisonQuery,
} from './requests'
import {
  AnnualStatsEnvelopeSchema,
  FireCalendarEnvelopeSchema,
  MonthlyComparisonEnvelopeSchema,
} from './responses'
import type {
  AnnualStatsData,
  FireCalendarData,
  MonthlyComparisonData,
} from './types'

export function useTemporalChartsApi() {
  const { getDailyActivity, getHistoricalCalendar } = useHotspotsApi()

  async function getAnnualStats(params?: AnnualStatsQuery): Promise<AnnualStatsData> {
    const qs = buildChartQueryString({ ...(params ?? {}) }, params?.polygon)
    const { data, error } = await useApiFetch(`/charts/temporal/annual-stats${qs}`).get().json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch annual stats')
    }
    return AnnualStatsEnvelopeSchema.parse(data.value).data
  }

  async function getMonthlyComparison(
    params?: MonthlyComparisonQuery,
  ): Promise<MonthlyComparisonData> {
    const qs = buildChartQueryString({ ...(params ?? {}) }, params?.polygon)
    const { data, error } = await useApiFetch(`/charts/temporal/monthly-comparison${qs}`)
      .get()
      .json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch monthly comparison')
    }
    return MonthlyComparisonEnvelopeSchema.parse(data.value).data
  }

  async function getFireCalendar(params: FireCalendarQuery): Promise<FireCalendarData> {
    const qs = buildChartQueryString({ ...params }, params.polygon)
    const { data, error } = await useApiFetch(`/charts/temporal/fire-calendar${qs}`).get().json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch fire calendar')
    }
    return FireCalendarEnvelopeSchema.parse(data.value).data
  }

  return {
    getDailyActivity,
    getHistoricalCalendar,
    getAnnualStats,
    getMonthlyComparison,
    getFireCalendar,
  }
}
