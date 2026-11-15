import type { z } from "zod";
import type {
  DailyActivityRequestSchema,
  HotspotFiltersRequestSchema,
} from "./requests";
import type {
  AvailableDatesResponseSchema,
  DailyActivityResponseSchema,
  HistoricalCalendarResponseSchema,
  HotspotResponseSchema,
  PaginatedHotspotResponseSchema,
} from "./responses";

export type HotspotFiltersRequest = z.infer<typeof HotspotFiltersRequestSchema>;
export type DailyActivityRequest = z.infer<typeof DailyActivityRequestSchema>;
export type HotspotResponse = z.infer<typeof HotspotResponseSchema>;
export type PaginatedHotspotResponse = z.infer<typeof PaginatedHotspotResponseSchema>;
export type AvailableDatesResponse = z.infer<typeof AvailableDatesResponseSchema>;
export type DailyActivityResponse = z.infer<typeof DailyActivityResponseSchema>;
export type HistoricalCalendarResponse = z.infer<typeof HistoricalCalendarResponseSchema>;
