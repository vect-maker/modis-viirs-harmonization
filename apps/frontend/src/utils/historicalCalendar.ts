import type { CalendarCell, CalendarSensor, HistoricalMonth } from '@/types/calendar'
import { getThermalPalette, getThermalZeroColor } from './themeColors.ts'

export function calendarCount(
  month: HistoricalMonth | undefined,
  sensor: CalendarSensor,
): number | null {
  if (!month) return null
  return sensor === 'MODIS' ? month.modisCount : sensor === 'VIIRS' ? month.viirsCount : month.total
}

export function buildCalendarRows(
  months: readonly HistoricalMonth[],
  firstYear: number,
  lastYear: number,
  sensor: CalendarSensor,
): { year: number; cells: CalendarCell[] }[] {
  const index = new Map(months.map((month) => [`${month.year}-${month.month}`, month]))
  return Array.from({ length: lastYear - firstYear + 1 }, (_, i) => lastYear - i).map((year) => ({
    year,
    cells: Array.from({ length: 12 }, (_, i) => ({
      year,
      month: i + 1,
      count: calendarCount(index.get(`${year}-${i + 1}`), sensor),
    })),
  }))
}

/** Shared logarithmic scale per sensor: the same count always gets the same color. */
export function calendarColor(count: number | null, maxCount: number): string {
  if (count === null) return 'transparent'
  if (count === 0) return getThermalZeroColor()
  const palette = getThermalPalette()
  const level = Math.min(4, Math.floor((Math.log1p(count) / Math.log1p(Math.max(1, maxCount))) * 5))
  return palette[level] ?? palette[0]!
}
