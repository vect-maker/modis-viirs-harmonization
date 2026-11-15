import type { z } from "zod";
import type {
  HealthLiveResponseSchema,
  HealthReadyResponseSchema,
  HealthStatusSchema,
} from "./responses";

export type HealthStatus = z.infer<typeof HealthStatusSchema>;
export type HealthLiveResponse = z.infer<typeof HealthLiveResponseSchema>;
export type HealthReadyResponse = z.infer<typeof HealthReadyResponseSchema>;
