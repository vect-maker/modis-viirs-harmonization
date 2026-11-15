import type { z } from "zod";
import type { PlatformFiltersRequestSchema } from "./requests";
import type { PaginatedPlatformResponseSchema, PlatformResponseSchema } from "./responses";

export type PlatformFiltersRequest = z.infer<typeof PlatformFiltersRequestSchema>;
export type PlatformResponse = z.infer<typeof PlatformResponseSchema>;
export type PaginatedPlatformResponse = z.infer<typeof PaginatedPlatformResponseSchema>;
