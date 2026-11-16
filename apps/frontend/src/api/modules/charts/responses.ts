import { z } from 'zod'
import { ChartResponseSchema } from '../shared/schemas'

export const DescriptiveStatsSchema = z.object({
  count: z.number().int().nonnegative(),
  sum: z.number().nullable(),
  mean: z.number().nullable(),
  std: z.number().nullable(),
  min: z.number().nullable(),
  p25: z.number().nullable(),
  median: z.number().nullable(),
  p75: z.number().nullable(),
  p90: z.number().nullable(),
  iqr: z.number().nullable(),
  max: z.number().nullable(),
})

export const AnnualRowSchema = z.object({
  year: z.number().int(),
  months_in_archive: z.number().int().min(0).max(12),
  complete: z.boolean(),
  provisional_months: z.number().int().min(0).max(12).default(0),
  total_hotspots: z.number().int().nonnegative(),
  modis_count: z.number().int().nonnegative(),
  viirs_count: z.number().int().nonnegative(),
  harmonized_index: z.number(),
  avg_frp: z.number().nullable().optional(),
  frp: DescriptiveStatsSchema.nullable().optional(),
  confidence: DescriptiveStatsSchema.nullable().optional(),
  bright_tir: DescriptiveStatsSchema.nullable().optional(),
  bright_mir: DescriptiveStatsSchema.nullable().optional(),
})

export const AnnualStatsDataSchema = z.object({
  range: z.object({ start_year: z.number().int(), end_year: z.number().int() }).nullable(),
  coverage: z.object({ first_detection: z.string(), last_detection: z.string() }).nullable(),
  rows: z.array(AnnualRowSchema),
})

export const MonthlyComparisonItemSchema = z.object({
  month: z.number().int().min(1).max(12),
  has_data: z.boolean(),
  archive_state: z.enum(['full', 'partial', 'missing']),
  provisional: z.boolean(),
  days_with_data: z.tuple([z.number().int(), z.number().int()]).nullable(),
  year_count: z.number().nullable(),
  year_raw_count: z.number().int().nullable(),
  year_sum_frp: z.number().nullable(),
  year_avg_frp: z.number().nullable(),
  historic: DescriptiveStatsSchema,
  anomaly_abs: z.number().nullable(),
  anomaly_pct: z.number().nullable(),
  anomaly_pct_median: z.number().nullable(),
  z_score: z.number().nullable(),
})

export const MonthlyComparisonDataSchema = z.object({
  year: z.number().int().nullable(),
  metric: z.enum(['raw', 'harmonized']),
  available_years: z.array(z.number().int()),
  baseline_years: z.array(z.number().int()),
  coverage: z.object({ first_detection: z.string(), last_detection: z.string() }).nullable(),
  months: z.array(MonthlyComparisonItemSchema),
})

export const FireCalendarIntervalSchema = z.object({
  date: z.string(),
  has_data: z.boolean().optional(),
  archive_state: z.enum(['full', 'partial', 'missing']).optional(),
  hotspot_count: z.number().int().nonnegative(),
  fire_count: z.number().int().nonnegative(),
  new_fires: z.number().int().nonnegative(),
  active_fires: z.number().int().nonnegative(),
  frp_total: z.number(),
  frp_average: z.number(),
  max_frp: z.number(),
  daytime_hotspots: z.number().int().nonnegative(),
  nighttime_hotspots: z.number().int().nonnegative(),
  high_confidence_count: z.number().int().nonnegative(),
})

export const FireCalendarDataSchema = z.object({
  period: z.object({
    year: z.number().int(),
    month: z.number().int().nullable(),
    start_date: z.string(),
    end_date: z.string(),
  }),
  aggregation: z.enum(['day', 'week', 'month']),
  total_hotspots: z.number().int().nonnegative(),
  total_fires: z.number().int().nonnegative(),
  new_fires: z.number().int().nonnegative(),
  active_fires: z.number().int().nonnegative(),
  frp_total: z.number(),
  frp_average: z.number(),
  max_frp: z.number(),
  daytime_hotspots: z.number().int().nonnegative(),
  nighttime_hotspots: z.number().int().nonnegative(),
  high_confidence_count: z.number().int().nonnegative(),
  intervals: z.array(FireCalendarIntervalSchema),
})

export const WeatherCorrelationRecordSchema = z.object({
  date: z.string(),
  is_complete: z.boolean(),
  wind_speed: z.number().nullable(),
  wind_direction_from_deg: z.number().nullable(),
  wind_direction_to_deg: z.number().nullable(),
  wind_u: z.number().nullable(),
  wind_v: z.number().nullable(),
  temperature: z.number().nullable(),
  humidity: z.number().nullable(),
  precipitation: z.number().nullable(),
  wind_fire_angle_diff_deg: z.number().nullable(),
  wind_fire_alignment_cos: z.number().nullable(),
  status_message: z.string(),
})

export const WeatherCorrelationDataSchema = z.object({
  records: z.array(WeatherCorrelationRecordSchema),
  total: z.number().int().nonnegative(),
})

export const AnnualStatsEnvelopeSchema = ChartResponseSchema(AnnualStatsDataSchema)
export const MonthlyComparisonEnvelopeSchema = ChartResponseSchema(MonthlyComparisonDataSchema)
export const FireCalendarEnvelopeSchema = ChartResponseSchema(FireCalendarDataSchema)
export const WeatherCorrelationEnvelopeSchema = ChartResponseSchema(WeatherCorrelationDataSchema)
