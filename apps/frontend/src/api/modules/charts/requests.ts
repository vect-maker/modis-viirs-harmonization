import type { GeoJSONPolygon } from 'zod-geojson'

export interface ChartBaseFilterQuery {
  start_date?: string
  end_date?: string
  country?: string
  polygon?: GeoJSONPolygon | null
  metric?: 'raw' | 'harmonized'
}

export interface AnnualStatsQuery extends ChartBaseFilterQuery {
  high_value?: number
  start_year?: number
  end_year?: number
  include_distributions?: boolean
}

export interface MonthlyComparisonQuery extends ChartBaseFilterQuery {
  year?: number | null
  start_year?: number
  end_year?: number
}

export interface FireCalendarQuery extends ChartBaseFilterQuery {
  year: number
  month?: number
  instrument?: string
  aggregation?: 'day' | 'week' | 'month'
}

export interface ConfidenceDbscanQuery extends ChartBaseFilterQuery {
  eps?: number | string
  min_samples?: number
  high_value?: number
}

export interface CorrelationsQuery extends ChartBaseFilterQuery {
  high_value?: number
}

export interface SpatialDensityQuery extends ChartBaseFilterQuery {
  cell_size_deg?: number | string
  min_lat?: number
  max_lat?: number
  min_lon?: number
  max_lon?: number
  limit?: number
}

export interface SpatialAnomaliesQuery extends ChartBaseFilterQuery {
  n_estimators?: number
  contamination?: number | string
  random_state?: number
  max_rows?: number
  max_points_returned?: number
  min_lat?: number
  max_lat?: number
  min_lon?: number
  max_lon?: number
}

export interface MonthlyForecastQuery extends ChartBaseFilterQuery {
  train_ratio?: number
  future_months?: number | string
  start_year?: number | string
  end_year?: number | string
}

export interface ClusterMovementQuery extends ChartBaseFilterQuery {
  min_lat?: number
  max_lat?: number
  min_lon?: number
  max_lon?: number
  eps_km?: number | string
  min_samples?: number
  time_window_hours?: number
  max_time_window_hours?: number
  interval_hours?: number
  max_rows?: number
  limit?: number
  offset?: number
}

export interface WeatherCorrelationQuery extends ChartBaseFilterQuery {
  latitude: number
  longitude: number
  start_date: string
  end_date: string
  fire_direction_deg?: number | null
  limit?: number
  offset?: number
}

export interface FirePredictQuery extends ClusterMovementQuery {
  min_training_samples?: number
  test_ratio?: number
  n_estimators?: number
}

export function polygonBbox(polygon: GeoJSONPolygon | null | undefined) {
  if (!polygon) return null
  const ring = polygon.coordinates[0]
  if (!ring || ring.length === 0) return null
  let minLon = Infinity
  let maxLon = -Infinity
  let minLat = Infinity
  let maxLat = -Infinity
  for (const pt of ring) {
    const lon = pt[0]
    const lat = pt[1]
    if (lon === undefined || lat === undefined) continue
    if (lon < minLon) minLon = lon
    if (lon > maxLon) maxLon = lon
    if (lat < minLat) minLat = lat
    if (lat > maxLat) maxLat = lat
  }
  return Number.isFinite(minLat) ? { minLat, maxLat, minLon, maxLon } : null
}

export function buildChartQueryString(
  params: Record<string, unknown>,
  polygon?: GeoJSONPolygon | null,
): string {
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (key === 'polygon' || value === undefined || value === null || value === '') {
      continue
    }
    qs.set(key, String(value))
  }
  if (polygon) {
    qs.set('polygon', JSON.stringify(polygon))
  }
  const str = qs.toString()
  return str ? `?${str}` : ''
}
