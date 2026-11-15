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
-- Preserves NULL FRP when native frp is NULL and normalizes VIIRS weights by
-- active VIIRS platform count per country-year.
-- Input:  data/temp/harmonize/01_base_points.parquet
--         data/temp/harmonize/02_quadrant_hourly.parquet
--         data/temp/harmonize/03_country_calibration.parquet
-- Output: data/processed/hotspots_harmonized.parquet
-- ==============================================================================
COPY (
    WITH platform_exposure AS (
        SELECT
            country,
            year(acq_datetime) AS obs_year,
            greatest(count(DISTINCT satellite) FILTER (WHERE instrument = 'VIIRS'), 1)::DOUBLE AS active_viirs_platforms
        FROM read_parquet('data/temp/harmonize/01_base_points.parquet')
        GROUP BY 1, 2
    )
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
            WHEN b.instrument = 'MODIS' AND q.point_id IS NOT NULL THEN 'MODIS_REDUNDANT_CODETECTION'
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'MORNING_TERRA' THEN 'MODIS_UNIQUE_MORNING'
            WHEN b.instrument = 'MODIS' AND year(b.acq_datetime) < 2012 THEN 'MODIS_HISTORICAL_PRE_2012'
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'AFTERNOON_AQUA_VIIRS' THEN 'MODIS_SOLO_AFTERNOON'
            ELSE 'MODIS_SOLO_OTHER'
        END AS harmonization_category,
        CASE
            WHEN b.instrument = 'VIIRS' THEN round(1.0 / coalesce(p.active_viirs_platforms, 1.0), 4)
            WHEN b.instrument = 'MODIS' AND q.point_id IS NOT NULL THEN 0.00
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'MORNING_TERRA' THEN coalesce(c.f_morning, 2.20)
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'AFTERNOON_AQUA_VIIRS' THEN coalesce(c.f_afternoon, 6.12)
            ELSE coalesce(c.f_night, 4.50)
        END AS harmonized_weight,
        CASE
            WHEN b.instrument = 'VIIRS' THEN b.frp
            WHEN b.instrument = 'MODIS' AND q.point_id IS NOT NULL THEN
                CASE WHEN b.frp IS NULL THEN NULL ELSE 0.00 END
            ELSE
                CASE WHEN b.frp IS NULL THEN NULL ELSE round(b.frp * coalesce(c.f_frp, 1.14), 2) END
        END AS harmonized_frp
    FROM read_parquet('data/temp/harmonize/01_base_points.parquet') b
    LEFT JOIN read_parquet('data/temp/harmonize/02_quadrant_hourly.parquet') q
      ON b.point_id = q.point_id
    LEFT JOIN read_parquet('data/temp/harmonize/03_country_calibration.parquet') c
      ON b.country = c.country
    LEFT JOIN platform_exposure p
      ON b.country = p.country
     AND year(b.acq_datetime) = p.obs_year
) TO 'data/processed/hotspots_harmonized.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
