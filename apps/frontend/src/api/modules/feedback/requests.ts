import { z } from "zod";
import { PaginationQuerySchema } from "@/api/modules/shared/schemas";
import { FeedbackClassificationSchema, FeedbackSeveritySchema } from "./domain";

export const HotspotFeedbackUpsertRequestSchema = z.object({
  classification: FeedbackClassificationSchema,
  severity: FeedbackSeveritySchema.nullable().optional(),
  comment: z.string().max(1000).nullable().optional(),
});

export const HotspotFeedbackBatchSummaryRequestSchema = z.object({
  hotspot_ids: z.array(z.uuid()).min(1).max(500),
});

export const HotspotFeedbackListQuerySchema = PaginationQuerySchema;
