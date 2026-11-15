import { z } from "zod";

export const HealthStatusSchema = z.enum(["ok", "error"]);

export const HealthLiveResponseSchema = z.object({
  status: z.literal("ok"),
});

export const HealthReadyResponseSchema = z.object({
  status: HealthStatusSchema,
  dependencies: z.record(z.string(), HealthStatusSchema),
});
