import type { z } from 'zod'
import type {
  AnnualRowSchema,
  AnnualStatsDataSchema,
  ClusterMovementDataSchema,
  ConfidenceDbscanDataSchema,
  CorrelationPairSchema,
  FireCalendarDataSchema,
  FirePredictDataSchema,
  MonthlyComparisonDataSchema,
  MonthlyForecastDataSchema,
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
export type MonthlyForecastData = z.infer<typeof MonthlyForecastDataSchema>
export type ClusterMovementData = z.infer<typeof ClusterMovementDataSchema>
export type WeatherCorrelationData = z.infer<typeof WeatherCorrelationDataSchema>
export type FirePredictData = z.infer<typeof FirePredictDataSchema>
