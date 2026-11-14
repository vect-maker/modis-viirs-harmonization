import { z } from "zod";
import { PaginatedResponseSchema } from "@/api/modules/shared/schemas";

export const PlatformResponseSchema = z.object({
  id: z.uuid(),
  satellite: z.string().max(50),
  instrument: z.string().max(20),
});

export const PaginatedPlatformResponseSchema = PaginatedResponseSchema(PlatformResponseSchema);
