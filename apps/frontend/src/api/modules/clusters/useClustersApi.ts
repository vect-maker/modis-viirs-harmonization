import { useApiFetch } from "@/api/useApiFetch";
import type {
  ClusterDetailResponse,
  ClusterGeoJsonParams,
  FireEventFeatureCollection,
} from "./types";

function buildClusterQueryString(params?: ClusterGeoJsonParams): string {
  const queryParams = new URLSearchParams();
  if (params?.bbox) queryParams.append("bbox", params.bbox);
  if (params?.start_date) queryParams.append("start_date", params.start_date);
  if (params?.end_date) queryParams.append("end_date", params.end_date);
  if (params?.status) queryParams.append("status", params.status);
  if (params?.min_hotspots !== undefined) {
    queryParams.append("min_hotspots", params.min_hotspots.toString());
  }
  if (params?.limit !== undefined) {
    queryParams.append("limit", params.limit.toString());
  }
  const qs = queryParams.toString();
  return qs ? `?${qs}` : "";
}

export const useClustersApi = () => {
  async function getClustersGeoJson(
    params?: ClusterGeoJsonParams,
  ): Promise<FireEventFeatureCollection> {
    const endpoint = `/clusters/geojson${buildClusterQueryString(params)}`;
    const { data, error } = await useApiFetch(endpoint).get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch fire events GeoJSON");
    }

    return data.value as FireEventFeatureCollection;
  }

  async function queryClustersGeoJson(
    payload: Record<string, unknown>,
  ): Promise<FireEventFeatureCollection> {
    const { data, error } = await useApiFetch("/clusters/geojson")
      .post(payload)
      .json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to query fire events GeoJSON");
    }

    return data.value as FireEventFeatureCollection;
  }

  async function getClusterDetail(
    clusterId: number,
    limit = 100,
  ): Promise<ClusterDetailResponse> {
    const endpoint = `/clusters/${clusterId}?limit=${limit}&offset=0`;
    const { data, error } = await useApiFetch(endpoint).get().json();

    if (error.value || !data.value) {
      throw error.value || new Error(`Failed to fetch cluster ${clusterId}`);
    }

    return data.value as ClusterDetailResponse;
  }

  return {
    getClustersGeoJson,
    queryClustersGeoJson,
    getClusterDetail,
  };
};
