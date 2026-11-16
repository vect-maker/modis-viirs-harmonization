import type { z } from 'zod'
import type {
  AnnualRowSchema,
  AnnualStatsDataSchema,
  FireCalendarDataSchema,
  MonthlyComparisonDataSchema,
  WeatherCorrelationDataSchema,
} from './responses'

export type AnnualRow = z.infer<typeof AnnualRowSchema>
export type AnnualStatsData = z.infer<typeof AnnualStatsDataSchema>
export type MonthlyComparisonData = z.infer<typeof MonthlyComparisonDataSchema>
export type FireCalendarData = z.infer<typeof FireCalendarDataSchema>
export type WeatherCorrelationData = z.infer<typeof WeatherCorrelationDataSchema>
