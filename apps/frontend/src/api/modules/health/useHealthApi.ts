import { useApiFetch } from "@/api/useApiFetch";
import { HealthLiveResponseSchema, HealthReadyResponseSchema } from "./responses";
import type { HealthLiveResponse, HealthReadyResponse } from "./types";

export const useHealthApi = () => {
  // GET /health/live
  async function getHealthLive(): Promise<HealthLiveResponse> {
    const { data, error } = await useApiFetch("/health/live").get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch live health status");
    }

    return HealthLiveResponseSchema.parse(data.value);
  }

  // GET /health/ready
  async function getHealthReady(): Promise<HealthReadyResponse> {
    const { data, error } = await useApiFetch("/health/ready").get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch readiness health status");
    }

    return HealthReadyResponseSchema.parse(data.value);
  }

  return {
    getHealthLive,
    getHealthReady,
  };
};
