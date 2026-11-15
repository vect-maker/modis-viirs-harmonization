import type { z } from "zod";
import type { CountryFiltersRequestSchema } from "./requests";
import type { CountryResponseSchema, PaginatedCountryResponseSchema } from "./responses";

export type CountryFiltersRequest = z.infer<typeof CountryFiltersRequestSchema>;
export type CountryResponse = z.infer<typeof CountryResponseSchema>;
export type PaginatedCountryResponse = z.infer<typeof PaginatedCountryResponseSchema>;
