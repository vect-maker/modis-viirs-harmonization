import { buildPaginationQueryString, useApiFetch } from "@/api/useApiFetch";
import {
  HotspotFeedbackBatchSummaryRequestSchema,
  HotspotFeedbackListQuerySchema,
  HotspotFeedbackUpsertRequestSchema,
} from "./requests";
import {
  HotspotFeedbackBatchSummaryResponseSchema,
  HotspotFeedbackListResponseSchema,
  HotspotFeedbackPublicSchema,
} from "./responses";
import type {
  HotspotFeedbackBatchSummaryRequest,
  HotspotFeedbackBatchSummaryResponse,
  HotspotFeedbackListQuery,
  HotspotFeedbackListResponse,
  HotspotFeedbackPublic,
  HotspotFeedbackUpsertRequest,
} from "./types";

export const useFeedbackApi = () => {
  // POST /hotspots/feedback/summary
  async function getFeedbackBatchSummary(
    payload: HotspotFeedbackBatchSummaryRequest,
  ): Promise<HotspotFeedbackBatchSummaryResponse> {
    const validated = HotspotFeedbackBatchSummaryRequestSchema.parse(payload);
    const { data, error } = await useApiFetch("/hotspots/feedback/summary")
      .post(validated)
      .json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch hotspot feedback summaries");
    }

    return HotspotFeedbackBatchSummaryResponseSchema.parse(data.value);
  }

  // GET /hotspots/{hotspot_id}/feedback
  async function getHotspotFeedback(
    hotspotId: string,
    params?: HotspotFeedbackListQuery,
  ): Promise<HotspotFeedbackListResponse> {
    const validated = params ? HotspotFeedbackListQuerySchema.parse(params) : undefined;
    const endpoint = `/hotspots/${encodeURIComponent(hotspotId)}/feedback${buildPaginationQueryString(validated)}`;

    const { data, error } = await useApiFetch(endpoint).get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch hotspot feedback");
    }

    return HotspotFeedbackListResponseSchema.parse(data.value);
  }

  // PUT /hotspots/{hotspot_id}/feedback
  async function upsertHotspotFeedback(
    hotspotId: string,
    payload: HotspotFeedbackUpsertRequest,
  ): Promise<HotspotFeedbackPublic> {
    const validated = HotspotFeedbackUpsertRequestSchema.parse(payload);
    const endpoint = `/hotspots/${encodeURIComponent(hotspotId)}/feedback`;
    const { data, error } = await useApiFetch(endpoint).put(validated).json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to submit hotspot feedback");
    }

    return HotspotFeedbackPublicSchema.parse(data.value);
  }

  // DELETE /hotspots/{hotspot_id}/feedback/me
  async function deleteMyHotspotFeedback(hotspotId: string): Promise<void> {
    const endpoint = `/hotspots/${encodeURIComponent(hotspotId)}/feedback/me`;
    const { error } = await useApiFetch(endpoint).delete();

    if (error.value) {
      throw error.value || new Error("Failed to delete hotspot feedback");
    }
  }

  return {
    getFeedbackBatchSummary,
    getHotspotFeedback,
    upsertHotspotFeedback,
    deleteMyHotspotFeedback,
  };
};
