import type { CountryResponse, HotspotResponse, PlatformResponse } from '@/api'
import type { HotspotDateRange } from '@/types/filters'

const columns = [
  'latitude',
  'longitude',
  'acq_datetime',
  'instrument',
  'satellite',
  'country',
  'confidence_class',
  'confidence',
  'frp',
  'bright_mir',
  'daynight',
] as const

function escapeCell(value: string | number | null | undefined) {
  const text = value == null ? '' : String(value)
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function hotspotsToCsv(
  hotspots: readonly HotspotResponse[],
  platformsById?: ReadonlyMap<string, PlatformResponse>,
  countriesById?: ReadonlyMap<string, CountryResponse>,
): string {
  const header = columns
    .map((column) => (column === 'acq_datetime' ? 'acq_datetime_utc' : column))
    .join(',')
  const rows = hotspots.map((hotspot) => {
    const platform = platformsById?.get(hotspot.platform_id)
    const country = countriesById?.get(hotspot.country_id)
    const values = [
      hotspot.latitude,
      hotspot.longitude,
      hotspot.acq_datetime,
      platform?.instrument ?? '',
      platform?.satellite ?? '',
      country?.name ?? '',
      hotspot.confidence_class,
      hotspot.confidence,
      hotspot.frp,
      hotspot.bright_mir,
      hotspot.daynight,
    ]
    return values.map(escapeCell).join(',')
  })
  return [header, ...rows].join('\r\n') + '\r\n'
}

export function hotspotCsvFilename(
  range: HotspotDateRange | null,
  sensor: string,
  selectedArea: boolean,
) {
  const period = range ? `${range.start}_${range.end}` : 'all-dates'
  return `nicaragua-hotspots_${selectedArea ? 'selected-area' : 'country'}_${sensor.toLowerCase()}_${period}.csv`
}
