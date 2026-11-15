-- Execution and memory optimizations
SET max_memory = '6GB';
SET temp_directory = 'data/temp/duckdb';
SET threads = 4;
SET preserve_insertion_order = false;

-- Enable live progress reporting in terminal
SET enable_progress_bar = true;
SET progress_bar_time = 500;

-- ==============================================================================
-- Harmonization Step 1: Enrich Silver points
-- Input:  data/processed/hotspots.parquet
-- Output: data/temp/harmonize/01_base_points.parquet
-- ==============================================================================
COPY (
    WITH solar AS (
        SELECT
            *,
            row_number() OVER () AS point_id,
            ((hour(acq_datetime) + minute(acq_datetime) / 60.0 + longitude / 15.0) % 24.0 + 24.0) % 24.0 AS local_solar_hour,
            floor(latitude / 0.02)::BIGINT AS lat_cell,
            floor((longitude * cos(radians(latitude))) / 0.02)::BIGINT AS lon_cell,
            floor(epoch(acq_datetime) / 3600.0)::BIGINT AS hour_slot
        FROM read_parquet('data/processed/hotspots.parquet')
    )
    SELECT
        point_id,
        country,
        latitude,
        longitude,
        bright_mir,
        scan,
        track,
        acq_datetime,
        satellite,
        instrument,
        confidence,
        confidence_class,
        version,
        bright_tir,
        frp,
        daynight,
        type,
        lat_cell,
        lon_cell,
        hour_slot,
        CASE
            WHEN local_solar_hour >= 8.5 AND local_solar_hour < 12.0 THEN 'MORNING_TERRA'
            WHEN local_solar_hour >= 12.0 AND local_solar_hour < 16.0 THEN 'AFTERNOON_AQUA_VIIRS'
            WHEN local_solar_hour >= 20.0 AND local_solar_hour < 23.5 THEN 'NIGHT_TERRA'
            WHEN local_solar_hour >= 23.5 OR local_solar_hour < 4.0 THEN 'NIGHT_DAWN_AQUA_VIIRS'
            ELSE 'OFF_CYCLE'
        END AS overpass_window
    FROM solar
) TO 'data/temp/harmonize/01_base_points.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
