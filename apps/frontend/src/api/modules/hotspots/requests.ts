import { z } from "zod";
import { PaginationQuerySchema } from "@/api/modules/shared/schemas";

export const HotspotFiltersRequestSchema = PaginationQuerySchema.extend({
  start_date: z.iso.date().optional(),
  end_date: z.iso.date().optional(),
});
