import { buildPaginationQueryString, useApiFetch } from "@/api/useApiFetch";
import { PlatformFiltersRequestSchema } from "./requests";
import { PaginatedPlatformResponseSchema } from "./responses";
import type { PaginatedPlatformResponse, PlatformFiltersRequest } from "./types";

export const usePlatformsApi = () => {
  // GET /platforms
  async function getPlatforms(params?: PlatformFiltersRequest): Promise<PaginatedPlatformResponse> {
    const validated = params ? PlatformFiltersRequestSchema.parse(params) : undefined;
    const endpoint = `/platforms${buildPaginationQueryString(validated)}`;

    const { data, error } = await useApiFetch(endpoint).get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch platforms");
    }

    return PaginatedPlatformResponseSchema.parse(data.value);
  }

  return {
    getPlatforms,
  };
};
