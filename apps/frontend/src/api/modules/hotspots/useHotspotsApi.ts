import { useApiFetch } from "@/api/useApiFetch";
import { ChartResponseSchema } from "../shared/schemas";
import { DailyActivityRequestSchema, HotspotFiltersRequestSchema } from "./requests";
import {
  AvailableDatesResponseSchema,
  DailyActivityResponseSchema,
  HistoricalCalendarResponseSchema,
  PaginatedHotspotResponseSchema,
} from "./responses";
import type {
  AvailableDatesResponse,
  DailyActivityRequest,
  DailyActivityResponse,
  HistoricalCalendarResponse,
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
  if (params?.polygon) {
    queryParams.append("polygon", JSON.stringify(params.polygon));
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

  // GET /charts/temporal/daily-activity
  async function getDailyActivity(params?: DailyActivityRequest): Promise<DailyActivityResponse> {
    const validated = params ? DailyActivityRequestSchema.parse(params) : undefined;
    const queryParams = new URLSearchParams();
    if (validated?.start_date) queryParams.append("start_date", validated.start_date);
    if (validated?.end_date) queryParams.append("end_date", validated.end_date);
    if (validated?.instrument) queryParams.append("instrument", validated.instrument);
    if (validated?.polygon) queryParams.append("polygon", JSON.stringify(validated.polygon));
    const qs = queryParams.toString();
    const endpoint = `/charts/temporal/daily-activity${qs ? `?${qs}` : ""}`;

    const { data, error } = await useApiFetch(endpoint).get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch daily hotspot activity");
    }

    return ChartResponseSchema(DailyActivityResponseSchema).parse(data.value).data;
  }

  // GET /charts/temporal/historical-calendar
  async function getHistoricalCalendar(): Promise<HistoricalCalendarResponse> {
    const { data, error } = await useApiFetch("/charts/temporal/historical-calendar").get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch historical calendar");
    }

    return ChartResponseSchema(HistoricalCalendarResponseSchema).parse(data.value).data;
  }

  return {
    getHotspots,
    getAvailableDates,
    getDailyActivity,
    getHistoricalCalendar,
  };
};
