import { buildPaginationQueryString, useApiFetch } from "@/api/useApiFetch";
import { CountryFiltersRequestSchema } from "./requests";
import { PaginatedCountryResponseSchema } from "./responses";
import type { CountryFiltersRequest, PaginatedCountryResponse } from "./types";

export const useCountriesApi = () => {
  // GET /countries
  async function getCountries(params?: CountryFiltersRequest): Promise<PaginatedCountryResponse> {
    const validated = params ? CountryFiltersRequestSchema.parse(params) : undefined;
    const endpoint = `/countries${buildPaginationQueryString(validated)}`;

    const { data, error } = await useApiFetch(endpoint).get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch countries");
    }

    return PaginatedCountryResponseSchema.parse(data.value);
  }

  return {
    getCountries,
  };
};
