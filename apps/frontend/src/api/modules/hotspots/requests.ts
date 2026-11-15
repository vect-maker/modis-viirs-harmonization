import { z } from "zod";
import { GeoJSONPolygonSchema } from "zod-geojson";
import { PaginationQuerySchema } from "@/api/modules/shared/schemas";

export const HotspotFiltersRequestSchema = PaginationQuerySchema.extend({
  start_date: z.iso.date().optional(),
  end_date: z.iso.date().optional(),
  polygon: GeoJSONPolygonSchema.optional(),
});

export const DailyActivityRequestSchema = z.object({
  start_date: z.iso.date().optional(),
  end_date: z.iso.date().optional(),
  instrument: z.enum(["MODIS", "VIIRS"]).optional(),
  polygon: GeoJSONPolygonSchema.optional(),
});
