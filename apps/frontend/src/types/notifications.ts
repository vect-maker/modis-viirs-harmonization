import { z } from "zod";

export const SSETargetScopeSchema = z.enum(["all", "user", "tenant"]);
export type SSETargetScope = z.infer<typeof SSETargetScopeSchema>;

export const NotificationSeveritySchema = z.enum(["info", "success", "warning", "error"]);
export type NotificationSeverity = z.infer<typeof NotificationSeveritySchema>;

export const SSEEventEnvelopeSchema = z.object({
  event_id: z.union([z.string(), z.number()]),
  emitter_service: z.string().default("firms-api"),
  target_scope: SSETargetScopeSchema.default("all"),
  target_id: z.string().nullable().optional(),
  event_type: z.string(),
  payload: z.record(z.string(), z.unknown()),
  timestamp: z.string(),
});

export type SSEEventEnvelope = z.infer<typeof SSEEventEnvelopeSchema>;

export type SSEConnectionStatus = "CONNECTING" | "OPEN" | "CLOSED";

export interface ToastNotification {
  id: string;
  eventId?: string;
  title: string;
  message: string;
  severity: NotificationSeverity;
  emitterService: string;
  eventType: string;
  timestamp: string;
  createdAtMs: number;
  durationMs: number;
  remainingMs: number;
  paused: boolean;
  payload: Record<string, unknown>;
}

export interface CreateToastInput {
  id?: string;
  eventId?: string;
  title: string;
  message: string;
  severity?: NotificationSeverity;
  emitterService?: string;
  eventType?: string;
  timestamp?: string;
  durationMs?: number;
  payload?: Record<string, unknown>;
}
