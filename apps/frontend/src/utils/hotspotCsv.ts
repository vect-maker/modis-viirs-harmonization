import type { FireHotspot } from '@/types/hotspot'
import type { HotspotDateRange } from '@/types/filters'

const columns = [
  'latitude',
  'longitude',
  'acq_datetime',
  'instrument',
  'satellite',
  'confidence_class',
  'confidence',
  'frp',
  'bright_mir',
  'daynight',
] as const satisfies readonly (keyof FireHotspot)[]

function escapeCell(value: string | number) {
  const text = String(value)
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function hotspotsToCsv(hotspots: readonly FireHotspot[]): string {
  const header = columns
    .map((column) => (column === 'acq_datetime' ? 'acq_datetime_utc' : column))
    .join(',')
  const rows = hotspots.map((hotspot) =>
    columns.map((column) => escapeCell(hotspot[column])).join(','),
  )
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
