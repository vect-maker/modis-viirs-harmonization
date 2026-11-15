import { z } from "zod";
import { PaginatedResponseSchema } from "@/api/modules/shared/schemas";
import { FeedbackClassificationSchema, FeedbackSeveritySchema } from "./domain";

export const HotspotFeedbackPublicSchema = z.object({
  id: z.uuid(),
  hotspot_id: z.uuid(),
  user_id: z.uuid(),
  username: z.string(),
  user_role: z.string(),
  classification: FeedbackClassificationSchema,
  severity: FeedbackSeveritySchema.nullable(),
  comment: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});

export const HotspotFeedbackSummarySchema = z.object({
  hotspot_id: z.uuid(),
  total_reports: z.number().int().nonnegative(),
  counts: z.record(FeedbackClassificationSchema, z.number().int().nonnegative()),
  consensus: FeedbackClassificationSchema.nullable(),
});

export const HotspotFeedbackListResponseSchema = z.object({
  summary: HotspotFeedbackSummarySchema,
  items: PaginatedResponseSchema(HotspotFeedbackPublicSchema),
  my_feedback: HotspotFeedbackPublicSchema.nullable().optional(),
});

export const HotspotFeedbackBatchSummaryResponseSchema = z.object({
  summaries: z.record(z.uuid(), HotspotFeedbackSummarySchema),
});
