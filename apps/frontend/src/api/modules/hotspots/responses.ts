import { z } from "zod";
import { PaginatedResponseSchema } from "@/api/modules/shared/schemas";

export const HotspotResponseSchema = z.object({
  id: z.uuid(),
  country_id: z.uuid(),
  platform_id: z.uuid(),
  latitude: z.number(),
  longitude: z.number(),
  acq_datetime: z.iso.datetime({ local: true }),
  bright_mir: z.number().nullable().optional(),
  bright_tir: z.number().nullable().optional(),
  scan: z.number().nullable().optional(),
  track: z.number().nullable().optional(),
  confidence: z.number().int().nullable().optional(),
  confidence_class: z.string().max(20).nullable().optional(),
  frp: z.number().nullable().optional(),
  daynight: z.string().max(5).nullable().optional(),
  type: z.number().int().nullable().optional(),
  version: z.string().max(20).nullable().optional(),
  overpass_window: z.string().max(30).nullable().optional(),
  harmonization_category: z.string().max(40).nullable().optional(),
  harmonized_weight: z.number().nullable().optional(),
  harmonized_frp: z.number().nullable().optional(),
});

export const PaginatedHotspotResponseSchema = PaginatedResponseSchema(HotspotResponseSchema);
