-- Execution and memory optimizations
SET max_memory = '6GB';
SET temp_directory = 'data/temp/duckdb';
SET threads = 4;
SET preserve_insertion_order = false;

-- Enable live progress reporting in terminal
SET enable_progress_bar = true;
SET progress_bar_time = 500;

-- ==============================================================================
-- Harmonization Step 2: Quadrant-hour co-occurrence summary
-- Input:  data/temp/harmonize/01_base_points.parquet
-- Output: data/temp/harmonize/02_quadrant_hourly.parquet
-- ==============================================================================
COPY (
    SELECT
        country,
        lat_q,
        lon_q,
        hour_window,
        count(*) FILTER (WHERE instrument = 'MODIS') AS modis_in_cluster,
        count(*) FILTER (WHERE instrument = 'VIIRS') AS viirs_in_cluster,
        sum(coalesce(frp, 0.0)) FILTER (WHERE instrument = 'MODIS') AS modis_frp_sum,
        sum(coalesce(frp, 0.0)) FILTER (WHERE instrument = 'VIIRS') AS viirs_frp_sum
    FROM read_parquet('data/temp/harmonize/01_base_points.parquet')
    GROUP BY 1, 2, 3, 4
) TO 'data/temp/harmonize/02_quadrant_hourly.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
