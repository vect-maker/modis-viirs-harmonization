import type { z } from "zod";
import type { ApiErrorPayloadSchema, PaginationQuerySchema } from "./schemas";

export type PaginationQuery = z.infer<typeof PaginationQuerySchema>;
export type ApiErrorPayload = z.infer<typeof ApiErrorPayloadSchema>;

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  limit: number;
  offset: number;
}
