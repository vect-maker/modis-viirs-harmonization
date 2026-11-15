import { parseDate } from '@internationalized/date'
import type { HotspotResponse } from '@/api'
import type { DailyHotspotActivity } from '@/types/hotspot'
import type { HotspotDateRange } from '@/types/filters'

/** Counts available records per UTC day; an empty bucket is not evidence of no fires. */
export function aggregateDailyActivity(
  hotspots: readonly HotspotResponse[],
  availableDates: HotspotDateRange | null,
): DailyHotspotActivity[] {
  if (!availableDates) return []
  const counts = new Map<string, number>()
  for (const hotspot of hotspots) {
    const day = hotspot.acq_datetime.slice(0, 10)
    counts.set(day, (counts.get(day) ?? 0) + 1)
  }
  const result: DailyHotspotActivity[] = []
  const end = parseDate(availableDates.end)
  for (
    let day = parseDate(availableDates.start);
    day.compare(end) <= 0;
    day = day.add({ days: 1 })
  ) {
    const date = day.toString()
    result.push({ date, count: counts.get(date) ?? 0 })
  }
  return result
}
