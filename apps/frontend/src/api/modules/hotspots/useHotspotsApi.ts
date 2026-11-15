import { buildPaginationQueryString, useApiFetch } from "@/api/useApiFetch";
import { HotspotFiltersRequestSchema } from "./requests";
import { PaginatedHotspotResponseSchema } from "./responses";
import type { HotspotFiltersRequest, PaginatedHotspotResponse } from "./types";

export const useHotspotsApi = () => {
  // GET /hotspots
  async function getHotspots(params?: HotspotFiltersRequest): Promise<PaginatedHotspotResponse> {
    const validated = params ? HotspotFiltersRequestSchema.parse(params) : undefined;
    const endpoint = `/hotspots${buildPaginationQueryString(validated)}`;

    const { data, error } = await useApiFetch(endpoint).get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch hotspots");
    }

    return PaginatedHotspotResponseSchema.parse(data.value);
  }

  return {
    getHotspots,
  };
};
