import { useApiFetch } from "@/api/useApiFetch";
import { HotspotFiltersRequestSchema } from "./requests";
import { AvailableDatesResponseSchema, PaginatedHotspotResponseSchema } from "./responses";
import type {
  AvailableDatesResponse,
  HotspotFiltersRequest,
  PaginatedHotspotResponse,
} from "./types";

function buildHotspotQueryString(params?: HotspotFiltersRequest): string {
  const queryParams = new URLSearchParams();
  if (params?.limit !== undefined) {
    queryParams.append("limit", params.limit.toString());
  }
  if (params?.offset !== undefined) {
    queryParams.append("offset", params.offset.toString());
  }
  if (params?.start_date) {
    queryParams.append("start_date", params.start_date);
  }
  if (params?.end_date) {
    queryParams.append("end_date", params.end_date);
  }
  const qs = queryParams.toString();
  return qs ? `?${qs}` : "";
}

export const useHotspotsApi = () => {
  // GET /hotspots
  async function getHotspots(params?: HotspotFiltersRequest): Promise<PaginatedHotspotResponse> {
    const validated = params ? HotspotFiltersRequestSchema.parse(params) : undefined;
    const endpoint = `/hotspots${buildHotspotQueryString(validated)}`;

    const { data, error } = await useApiFetch(endpoint).get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch hotspots");
    }

    return PaginatedHotspotResponseSchema.parse(data.value);
  }

  // GET /hotspots/available-dates
  async function getAvailableDates(): Promise<AvailableDatesResponse> {
    const { data, error } = await useApiFetch("/hotspots/available-dates").get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch available hotspot dates");
    }

    return AvailableDatesResponseSchema.parse(data.value);
  }

  return {
    getHotspots,
    getAvailableDates,
  };
};
