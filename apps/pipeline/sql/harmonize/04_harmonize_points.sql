-- Execution and memory optimizations
SET max_memory = '6GB';
SET temp_directory = 'data/temp/duckdb';
SET threads = 4;
SET preserve_insertion_order = false;

-- Enable live progress reporting in terminal
SET enable_progress_bar = true;
SET progress_bar_time = 500;

-- ==============================================================================
-- Harmonization Step 4: Assign point-level category, weight, and calibrated FRP
-- Input:  data/temp/harmonize/01_base_points.parquet
--         data/temp/harmonize/02_quadrant_hourly.parquet
--         data/temp/harmonize/03_country_calibration.parquet
-- Output: data/processed/hotspots_harmonized.parquet
-- ==============================================================================
COPY (
    SELECT
        b.country,
        b.latitude,
        b.longitude,
        b.bright_mir,
        b.scan,
        b.track,
        b.acq_datetime,
        b.satellite,
        b.instrument,
        b.confidence,
        b.confidence_class,
        b.version,
        b.bright_tir,
        b.frp,
        b.daynight,
        b.type,
        b.overpass_window,
        CASE
            WHEN b.instrument = 'VIIRS' THEN 'VIIRS_PRESERVED'
            WHEN b.instrument = 'MODIS' AND coalesce(q.viirs_in_cluster, 0) > 0 THEN 'MODIS_REDUNDANT_CODETECTION'
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'MORNING_TERRA' THEN 'MODIS_UNIQUE_MORNING'
            WHEN b.instrument = 'MODIS' AND year(b.acq_datetime) < 2012 THEN 'MODIS_HISTORICAL_PRE_2012'
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'AFTERNOON_AQUA_VIIRS' THEN 'MODIS_SOLO_AFTERNOON'
            ELSE 'MODIS_SOLO_OTHER'
        END AS harmonization_category,
        CASE
            WHEN b.instrument = 'VIIRS' THEN 1.00
            WHEN b.instrument = 'MODIS' AND coalesce(q.viirs_in_cluster, 0) > 0 THEN 0.00
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'MORNING_TERRA' THEN coalesce(c.f_morning, 2.20)
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'AFTERNOON_AQUA_VIIRS' THEN coalesce(c.f_afternoon, 6.12)
            ELSE coalesce(c.f_night, 4.50)
        END AS harmonized_weight,
        CASE
            WHEN b.instrument = 'VIIRS' THEN coalesce(b.frp, 0.0)
            WHEN b.instrument = 'MODIS' AND coalesce(q.viirs_in_cluster, 0) > 0 THEN 0.00
            ELSE round(coalesce(b.frp, 0.0) * coalesce(c.f_frp, 1.14), 2)
        END AS harmonized_frp
    FROM read_parquet('data/temp/harmonize/01_base_points.parquet') b
    LEFT JOIN (
        SELECT
            country,
            lat_q,
            lon_q,
            hour_window,
            viirs_in_cluster
        FROM read_parquet('data/temp/harmonize/02_quadrant_hourly.parquet')
        WHERE viirs_in_cluster > 0
    ) q
      ON b.country = q.country
     AND b.lat_q = q.lat_q
     AND b.lon_q = q.lon_q
     AND b.hour_window = q.hour_window
    LEFT JOIN read_parquet('data/temp/harmonize/03_country_calibration.parquet') c
      ON b.country = c.country
) TO 'data/processed/hotspots_harmonized.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
