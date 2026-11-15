import { defineStore } from "pinia";
import { ref } from "vue";
import {
  useFeedbackApi,
  type HotspotFeedbackListResponse,
  type HotspotFeedbackSummary,
  type HotspotFeedbackUpsertRequest,
} from "@/api";

const BATCH_SIZE = 500;

export const useFeedbackStore = defineStore("feedback", () => {
  const feedbackApi = useFeedbackApi();

  const summariesByHotspotId = ref<Record<string, HotspotFeedbackSummary>>({});
  const activeHotspotId = ref<string | null>(null);
  const activeList = ref<HotspotFeedbackListResponse | null>(null);
  const isLoadingList = ref(false);
  const isSubmitting = ref(false);
  const error = ref<string | null>(null);

  async function fetchBatchSummaries(hotspotIds: string[]): Promise<void> {
    const uniqueIds = Array.from(new Set(hotspotIds)).filter(Boolean);
    if (uniqueIds.length === 0) return;

    for (let i = 0; i < uniqueIds.length; i += BATCH_SIZE) {
      const chunk = uniqueIds.slice(i, i + BATCH_SIZE);
      try {
        const res = await feedbackApi.getFeedbackBatchSummary({
          hotspot_ids: chunk,
        });
        summariesByHotspotId.value = {
          ...summariesByHotspotId.value,
          ...res.summaries,
        };
      } catch {
        // Non-fatal: keep map usable even if summary endpoint is temporarily unavailable
      }
    }
  }

  async function openHotspotFeedback(hotspotId: string): Promise<void> {
    activeHotspotId.value = hotspotId;
    isLoadingList.value = true;
    error.value = null;
    try {
      const res = await feedbackApi.getHotspotFeedback(hotspotId, {
        limit: 50,
        offset: 0,
      });
      activeList.value = res;
      summariesByHotspotId.value = {
        ...summariesByHotspotId.value,
        [hotspotId]: res.summary,
      };
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Failed to load hotspot feedback";
    } finally {
      isLoadingList.value = false;
    }
  }

  function closeHotspotFeedback(): void {
    activeHotspotId.value = null;
    activeList.value = null;
    error.value = null;
  }

  async function submitFeedback(
    hotspotId: string,
    payload: HotspotFeedbackUpsertRequest,
  ): Promise<void> {
    isSubmitting.value = true;
    error.value = null;
    try {
      await feedbackApi.upsertHotspotFeedback(hotspotId, payload);
      await openHotspotFeedback(hotspotId);
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Failed to submit feedback";
      throw err;
    } finally {
      isSubmitting.value = false;
    }
  }

  async function deleteMyFeedback(hotspotId: string): Promise<void> {
    isSubmitting.value = true;
    error.value = null;
    try {
      await feedbackApi.deleteMyHotspotFeedback(hotspotId);
      await openHotspotFeedback(hotspotId);
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Failed to delete feedback";
      throw err;
    } finally {
      isSubmitting.value = false;
    }
  }

  function ingestSSEFeedbackEvent(rawData: string): void {
    try {
      const envelope = JSON.parse(rawData) as {
        payload?: {
          hotspot_id?: string;
          summary?: HotspotFeedbackSummary;
        };
      };
      const hotspotId = envelope.payload?.hotspot_id;
      const summary = envelope.payload?.summary;
      if (!hotspotId || !summary) return;

      summariesByHotspotId.value = {
        ...summariesByHotspotId.value,
        [hotspotId]: summary,
      };

      if (activeHotspotId.value === hotspotId) {
        void openHotspotFeedback(hotspotId);
      }
    } catch {
      // Ignore malformed SSE frames
    }
  }

  return {
    summariesByHotspotId,
    activeHotspotId,
    activeList,
    isLoadingList,
    isSubmitting,
    error,
    fetchBatchSummaries,
    openHotspotFeedback,
    closeHotspotFeedback,
    submitFeedback,
    deleteMyFeedback,
    ingestSSEFeedbackEvent,
  };
});
