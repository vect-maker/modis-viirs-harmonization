import { z } from "zod";
import { PaginatedResponseSchema } from "@/api/modules/shared/schemas";

export const CountryResponseSchema = z.object({
  id: z.uuid(),
  name: z.string().max(100),
});

export const PaginatedCountryResponseSchema = PaginatedResponseSchema(CountryResponseSchema);
