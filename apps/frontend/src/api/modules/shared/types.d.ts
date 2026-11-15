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

export interface ChartMeta {
  metric: "raw" | "harmonized";
  filters: Record<string, unknown>;
  coverage?: Record<string, unknown> | null;
  generated_at: string;
}

export interface ChartResponse<T> {
  chart: string;
  meta: ChartMeta;
  data: T;
}
