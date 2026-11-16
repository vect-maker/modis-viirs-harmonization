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

export interface WeatherCorrelationQuery extends ChartBaseFilterQuery {
  latitude: number
  longitude: number
  start_date: string
  end_date: string
  fire_direction_deg?: number | null
  limit?: number
  offset?: number
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
