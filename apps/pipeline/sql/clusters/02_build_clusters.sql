-- =============================================================================
-- 02_build_clusters.sql
-- Computes Fire Event geometries and aggregates using DuckDB Spatial.
--
-- Input  : data/temp/clusters/assigned_hotspots.parquet
-- Output : data/clusters/fire_clusters.parquet
--          data/clusters/cluster_hotspots.parquet
-- =============================================================================

SET max_memory = '10GB';
SET threads = 8;

INSTALL spatial;
LOAD spatial;
SET geometry_always_xy = true;

COPY (
    WITH grouped AS (
        SELECT
            cluster_id,
            COUNT(*)::INTEGER AS hotspot_count,
            COUNT(*) FILTER (WHERE instrument = 'MODIS')::INTEGER AS modis_count,
            COUNT(*) FILTER (WHERE instrument = 'VIIRS')::INTEGER AS viirs_count,
            MIN(acq_datetime) AS datetime_start,
            MAX(acq_datetime) AS datetime_end,
            ROUND(COALESCE(MAX(frp), 0.0), 4) AS max_frp,
            ROUND(SUM(COALESCE(frp, 0.0)), 4) AS total_frp,
            ROUND(SUM(COALESCE(harmonized_weight, 1.0)), 4) AS harmonized_weight,
            ST_Centroid(ST_Collect(LIST(ST_Point(longitude, latitude)))) AS centroid_geom,
            ST_Buffer(
                ST_ConvexHull(ST_Collect(LIST(ST_Point(longitude, latitude)))),
                0.0036,
                8
            ) AS perimeter_geom
        FROM read_parquet('data/temp/clusters/assigned_hotspots.parquet')
        GROUP BY cluster_id
    )
    SELECT
        cluster_id,
        hotspot_count,
        modis_count,
        viirs_count,
        datetime_start,
        datetime_end,
        max_frp,
        total_frp,
        harmonized_weight,
        ROUND(ST_Y(centroid_geom), 6) AS centroid_lat,
        ROUND(ST_X(centroid_geom), 6) AS centroid_lon,
        ROUND(ST_Area_Spheroid(perimeter_geom) / 1000000.0, 4) AS area_km2,
        ST_AsText(centroid_geom) AS centroid_wkt,
        ST_AsText(perimeter_geom) AS geom_wkt
    FROM grouped
    ORDER BY cluster_id
) TO 'data/clusters/fire_clusters.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);

COPY (
    SELECT
        cluster_id,
        hotspot_id
    FROM read_parquet('data/temp/clusters/assigned_hotspots.parquet')
    ORDER BY cluster_id, hotspot_id
) TO 'data/clusters/cluster_hotspots.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
