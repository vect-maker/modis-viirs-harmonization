import { z } from "zod";

export const PaginationQuerySchema = z.object({
  limit: z.number().int().min(1).max(100).optional(),
  offset: z.number().int().min(0).optional(),
});

export const PaginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    data: z.array(itemSchema),
    total: z.number().int().nonnegative(),
    limit: z.number().int().nonnegative(),
    offset: z.number().int().nonnegative(),
  });

export const FastApiValidationErrorItemSchema = z.object({
  loc: z.array(z.union([z.string(), z.number()])),
  msg: z.string(),
  type: z.string(),
});

export const ApiErrorPayloadSchema = z.union([
  z.object({
    detail: z.string(),
  }),
  z.object({
    detail: z.array(FastApiValidationErrorItemSchema),
  }),
  z.object({
    message: z.string(),
  }),
]);
