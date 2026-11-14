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
-- Falls back to Central America reference defaults (2.20, 6.12, 4.50, 1.14)
-- when a country has fewer than 100 Class A co-detection clusters.
-- Input:  data/temp/harmonize/01_base_points.parquet
--         data/temp/harmonize/02_quadrant_hourly.parquet
-- Output: data/temp/harmonize/03_country_calibration.parquet
-- ==============================================================================
COPY (
    WITH class_a AS (
        SELECT
            country,
            count(*) AS class_a_clusters,
            sum(viirs_in_cluster)::DOUBLE / nullif(sum(modis_in_cluster), 0) AS raw_pixel_ratio,
            sum(viirs_frp_sum)::DOUBLE / nullif(sum(modis_frp_sum), 0) AS raw_frp_ratio
        FROM read_parquet('data/temp/harmonize/02_quadrant_hourly.parquet')
        WHERE year(hour_window) >= 2012
          AND modis_in_cluster > 0
          AND viirs_in_cluster > 0
        GROUP BY country
    ),
    overlap_totals AS (
        SELECT
            country,
            count(*) FILTER (WHERE instrument = 'VIIRS' AND overpass_window = 'AFTERNOON_AQUA_VIIRS')::DOUBLE
                / nullif(count(*) FILTER (WHERE instrument = 'MODIS' AND overpass_window = 'AFTERNOON_AQUA_VIIRS'), 0) AS raw_afternoon_ratio,
            count(*) FILTER (WHERE instrument = 'VIIRS' AND overpass_window IN ('NIGHT_TERRA', 'NIGHT_DAWN_AQUA_VIIRS', 'OFF_CYCLE'))::DOUBLE
                / nullif(count(*) FILTER (WHERE instrument = 'MODIS' AND overpass_window IN ('NIGHT_TERRA', 'NIGHT_DAWN_AQUA_VIIRS', 'OFF_CYCLE')), 0) AS raw_night_ratio
        FROM read_parquet('data/temp/harmonize/01_base_points.parquet')
        WHERE year(acq_datetime) >= 2012
        GROUP BY country
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
