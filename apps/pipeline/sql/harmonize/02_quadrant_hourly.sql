-- Execution and memory optimizations
SET max_memory = '6GB';
SET temp_directory = 'data/temp/duckdb';
SET threads = 4;
SET preserve_insertion_order = false;

-- Enable live progress reporting in terminal
SET enable_progress_bar = true;
SET progress_bar_time = 500;

-- ==============================================================================
-- Harmonization Step 2: Rolling spatio-temporal MODIS-VIIRS co-occurrence match
-- Uses 3x3x3 neighbor cell expansion + exact <= 2200m & <= 3600s tolerance
-- to eliminate fixed-grid and UTC hour-boundary artifacts.
-- Input:  data/temp/harmonize/01_base_points.parquet
-- Output: data/temp/harmonize/02_quadrant_hourly.parquet
-- ==============================================================================
COPY (
    WITH modis AS (
        SELECT
            point_id,
            country,
            latitude,
            longitude,
            acq_datetime,
            lat_cell,
            lon_cell,
            hour_slot
        FROM read_parquet('data/temp/harmonize/01_base_points.parquet')
        WHERE instrument = 'MODIS'
    ),
    viirs AS (
        SELECT
            point_id,
            country,
            latitude,
            longitude,
            acq_datetime,
            lat_cell,
            lon_cell,
            hour_slot
        FROM read_parquet('data/temp/harmonize/01_base_points.parquet')
        WHERE instrument = 'VIIRS'
    ),
    modis_neighbors AS (
        SELECT
            m.point_id,
            m.country,
            m.latitude,
            m.longitude,
            m.acq_datetime,
            m.lat_cell + dlat AS target_lat_cell,
            m.lon_cell + dlon AS target_lon_cell,
            m.hour_slot + dhr AS target_hour_slot
        FROM modis m
        CROSS JOIN UNNEST([-1, 0, 1]) AS t_lat(dlat)
        CROSS JOIN UNNEST([-1, 0, 1]) AS t_lon(dlon)
        CROSS JOIN UNNEST([-1, 0, 1]) AS t_hr(dhr)
    ),
    matches AS (
        SELECT
            mn.point_id AS modis_point_id,
            v.point_id AS viirs_point_id
        FROM modis_neighbors mn
        INNER JOIN viirs v
            ON mn.country = v.country
           AND mn.target_lat_cell = v.lat_cell
           AND mn.target_lon_cell = v.lon_cell
           AND mn.target_hour_slot = v.hour_slot
        WHERE abs(epoch(mn.acq_datetime) - epoch(v.acq_datetime)) <= 3600.0
          AND 111320.0 * sqrt(
              pow(mn.latitude - v.latitude, 2) +
              pow((mn.longitude - v.longitude) * cos(radians((mn.latitude + v.latitude) / 2.0)), 2)
          ) <= 2200.0
    )
    SELECT DISTINCT modis_point_id AS point_id
    FROM matches
    UNION ALL
    SELECT DISTINCT viirs_point_id AS point_id
    FROM matches
) TO 'data/temp/harmonize/02_quadrant_hourly.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
