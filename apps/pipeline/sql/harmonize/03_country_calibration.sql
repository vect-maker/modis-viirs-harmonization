-- Execution and memory optimizations
SET max_memory = '6GB';
SET temp_directory = 'data/temp/duckdb';
SET threads = 4;
SET preserve_insertion_order = false;

-- Enable live progress reporting in terminal
SET enable_progress_bar = true;
SET progress_bar_time = 500;

-- ==============================================================================
-- Harmonization Step 3: Empirical per-country calibration (2012+ overlap era)
-- Normalizes VIIRS counts/FRP by active VIIRS platform count per country-year
-- and falls back to reference defaults (2.20, 6.12, 4.50, 1.14) when a country
-- has fewer than 100 co-occurring MODIS observations.
-- Input:  data/temp/harmonize/01_base_points.parquet
--         data/temp/harmonize/02_quadrant_hourly.parquet
-- Output: data/temp/harmonize/03_country_calibration.parquet
-- ==============================================================================
COPY (
    WITH platform_exposure AS (
        SELECT
            country,
            year(acq_datetime) AS obs_year,
            greatest(count(DISTINCT satellite) FILTER (WHERE instrument = 'VIIRS'), 1)::DOUBLE AS active_viirs_platforms
        FROM read_parquet('data/temp/harmonize/01_base_points.parquet')
        GROUP BY 1, 2
    ),
    class_a AS (
        SELECT
            b.country,
            count(*) FILTER (WHERE b.instrument = 'MODIS') AS class_a_clusters,
            (sum(1.0 / p.active_viirs_platforms) FILTER (WHERE b.instrument = 'VIIRS'))::DOUBLE
                / nullif(count(*) FILTER (WHERE b.instrument = 'MODIS'), 0) AS raw_pixel_ratio,
            (sum(b.frp / p.active_viirs_platforms) FILTER (WHERE b.instrument = 'VIIRS'))::DOUBLE
                / nullif(sum(b.frp) FILTER (WHERE b.instrument = 'MODIS'), 0) AS raw_frp_ratio
        FROM read_parquet('data/temp/harmonize/02_quadrant_hourly.parquet') q
        INNER JOIN read_parquet('data/temp/harmonize/01_base_points.parquet') b
            ON q.point_id = b.point_id
        INNER JOIN platform_exposure p
            ON b.country = p.country
           AND year(b.acq_datetime) = p.obs_year
        WHERE year(b.acq_datetime) >= 2012
        GROUP BY b.country
    ),
    overlap_totals AS (
        SELECT
            b.country,
            (sum(1.0 / p.active_viirs_platforms) FILTER (WHERE b.instrument = 'VIIRS' AND b.overpass_window = 'AFTERNOON_AQUA_VIIRS'))::DOUBLE
                / nullif(count(*) FILTER (WHERE b.instrument = 'MODIS' AND b.overpass_window = 'AFTERNOON_AQUA_VIIRS'), 0) AS raw_afternoon_ratio,
            (sum(1.0 / p.active_viirs_platforms) FILTER (WHERE b.instrument = 'VIIRS' AND b.overpass_window IN ('NIGHT_TERRA', 'NIGHT_DAWN_AQUA_VIIRS', 'OFF_CYCLE')))::DOUBLE
                / nullif(count(*) FILTER (WHERE b.instrument = 'MODIS' AND b.overpass_window IN ('NIGHT_TERRA', 'NIGHT_DAWN_AQUA_VIIRS', 'OFF_CYCLE')), 0) AS raw_night_ratio
        FROM read_parquet('data/temp/harmonize/01_base_points.parquet') b
        INNER JOIN platform_exposure p
            ON b.country = p.country
           AND year(b.acq_datetime) = p.obs_year
        WHERE year(b.acq_datetime) >= 2012
        GROUP BY b.country
    )
    SELECT
        o.country,
        CASE
            WHEN coalesce(a.class_a_clusters, 0) >= 100 AND a.raw_pixel_ratio IS NOT NULL
                THEN round(greatest(1.0, least(a.raw_pixel_ratio, 10.0)), 2)
            ELSE 2.20
        END AS f_morning,
        CASE
            WHEN coalesce(a.class_a_clusters, 0) >= 100 AND o.raw_afternoon_ratio IS NOT NULL
                THEN round(greatest(1.0, least(o.raw_afternoon_ratio, 20.0)), 2)
            ELSE 6.12
        END AS f_afternoon,
        CASE
            WHEN coalesce(a.class_a_clusters, 0) >= 100 AND o.raw_night_ratio IS NOT NULL
                THEN round(greatest(1.0, least(o.raw_night_ratio, 15.0)), 2)
            ELSE 4.50
        END AS f_night,
        CASE
            WHEN coalesce(a.class_a_clusters, 0) >= 100 AND a.raw_frp_ratio IS NOT NULL
                THEN round(greatest(0.5, least(a.raw_frp_ratio, 5.0)), 2)
            ELSE 1.14
        END AS f_frp
    FROM overlap_totals o
    LEFT JOIN class_a a
      ON o.country = a.country
) TO 'data/temp/harmonize/03_country_calibration.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
