import type { z } from "zod";
import type { HotspotFiltersRequestSchema } from "./requests";
import type { HotspotResponseSchema, PaginatedHotspotResponseSchema } from "./responses";

export type HotspotFiltersRequest = z.infer<typeof HotspotFiltersRequestSchema>;
export type HotspotResponse = z.infer<typeof HotspotResponseSchema>;
export type PaginatedHotspotResponse = z.infer<typeof PaginatedHotspotResponseSchema>;
