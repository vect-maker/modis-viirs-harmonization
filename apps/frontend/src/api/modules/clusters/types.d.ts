import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { HotspotResponse } from "@/api/modules/hotspots/types";

export interface FireEventProperties {
  id: number;
  status: "ACTIVO" | "AISLADO" | "FINALIZADO" | string;
  datetime_start: string | null;
  datetime_end: string | null;
  duration_h: number;
  max_frp: number | null;
  total_frp: number | null;
  harmonized_weight: number | null;
  area_km2: number;
  centroid_lat: number | null;
  centroid_lon: number | null;
  hotspot_count: number;
  modis_count: number;
  viirs_count: number;
}

export type FireEventFeature = Feature<Geometry, FireEventProperties>;
export type FireEventFeatureCollection = FeatureCollection<Geometry, FireEventProperties>;

export interface ClusterGeoJsonParams {
  bbox?: string;
  start_date?: string;
  end_date?: string;
  status?: string;
  min_hotspots?: number;
  limit?: number;
}

export interface ClusterHotspotItem extends HotspotResponse {
  instrument?: string | null;
  satellite?: string | null;
}

export interface ClusterDetailResponse {
  data: {
    cluster: {
      id: number;
      status: string;
      datetimeStart: string | null;
      datetimeEnd: string | null;
      maxFrp: number | null;
      area_km2: number;
      hotspot_count: number;
      modis_count: number;
      viirs_count: number;
    };
    hotspots: ClusterHotspotItem[];
  };
  total: number;
  limit: number;
  offset: number;
}
