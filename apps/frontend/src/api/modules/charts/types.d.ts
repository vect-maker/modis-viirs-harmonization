import type { z } from 'zod'
import type {
  AnnualRowSchema,
  AnnualStatsDataSchema,
  ConfidenceDbscanDataSchema,
  CorrelationPairSchema,
  FireCalendarDataSchema,
  MonthlyComparisonDataSchema,
  SpatialAnomaliesDataSchema,
  SpatialDensityDataSchema,
  WeatherCorrelationDataSchema,
} from './responses'

export type AnnualRow = z.infer<typeof AnnualRowSchema>
export type AnnualStatsData = z.infer<typeof AnnualStatsDataSchema>
export type MonthlyComparisonData = z.infer<typeof MonthlyComparisonDataSchema>
export type FireCalendarData = z.infer<typeof FireCalendarDataSchema>
export type ConfidenceDbscanData = z.infer<typeof ConfidenceDbscanDataSchema>
export type CorrelationPair = z.infer<typeof CorrelationPairSchema>
export type SpatialDensityData = z.infer<typeof SpatialDensityDataSchema>
export type SpatialAnomaliesData = z.infer<typeof SpatialAnomaliesDataSchema>
export type WeatherCorrelationData = z.infer<typeof WeatherCorrelationDataSchema>
