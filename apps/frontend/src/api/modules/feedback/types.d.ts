import type { z } from "zod";
import type { FeedbackClassificationSchema, FeedbackSeveritySchema } from "./domain";
import type {
  HotspotFeedbackBatchSummaryRequestSchema,
  HotspotFeedbackListQuerySchema,
  HotspotFeedbackUpsertRequestSchema,
} from "./requests";
import type {
  HotspotFeedbackBatchSummaryResponseSchema,
  HotspotFeedbackListResponseSchema,
  HotspotFeedbackPublicSchema,
  HotspotFeedbackSummarySchema,
} from "./responses";

export type FeedbackClassification = z.infer<typeof FeedbackClassificationSchema>;
export type FeedbackSeverity = z.infer<typeof FeedbackSeveritySchema>;
export type HotspotFeedbackUpsertRequest = z.infer<typeof HotspotFeedbackUpsertRequestSchema>;
export type HotspotFeedbackBatchSummaryRequest = z.infer<
  typeof HotspotFeedbackBatchSummaryRequestSchema
>;
export type HotspotFeedbackListQuery = z.infer<typeof HotspotFeedbackListQuerySchema>;
export type HotspotFeedbackPublic = z.infer<typeof HotspotFeedbackPublicSchema>;
export type HotspotFeedbackSummary = z.infer<typeof HotspotFeedbackSummarySchema>;
export type HotspotFeedbackListResponse = z.infer<typeof HotspotFeedbackListResponseSchema>;
export type HotspotFeedbackBatchSummaryResponse = z.infer<
  typeof HotspotFeedbackBatchSummaryResponseSchema
>;
