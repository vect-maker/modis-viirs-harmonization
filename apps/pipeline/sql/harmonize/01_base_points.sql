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
            ((hour(acq_datetime) + minute(acq_datetime) / 60.0 + longitude / 15.0) % 24.0 + 24.0) % 24.0 AS local_solar_hour,
            round(latitude / 0.02) * 0.02 AS lat_q,
            round((longitude * cos(radians(latitude))) / 0.02) * 0.02 AS lon_q,
            date_trunc('hour', acq_datetime) AS hour_window
        FROM read_parquet('data/processed/hotspots.parquet')
    )
    SELECT
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
        lat_q,
        lon_q,
        hour_window,
        CASE
            WHEN local_solar_hour >= 8.5 AND local_solar_hour < 12.0 THEN 'MORNING_TERRA'
            WHEN local_solar_hour >= 12.0 AND local_solar_hour < 16.0 THEN 'AFTERNOON_AQUA_VIIRS'
            WHEN local_solar_hour >= 20.0 AND local_solar_hour < 23.5 THEN 'NIGHT_TERRA'
            WHEN local_solar_hour >= 23.5 OR local_solar_hour < 4.0 THEN 'NIGHT_DAWN_AQUA_VIIRS'
            ELSE 'OFF_CYCLE'
        END AS overpass_window
    FROM solar
) TO 'data/temp/harmonize/01_base_points.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
