-- Execution and memory optimizations
SET max_memory = '10GB';
SET temp_directory = 'data/temp/duckdb';
SET threads = 8;
SET preserve_insertion_order = false;

-- Enable live progress reporting in terminal
SET enable_progress_bar = true;
SET progress_bar_time = 500;

-- ==============================================================================
-- Universal Spatio-Temporal MODIS & VIIRS Harmonization
-- Input:  data/processed/hotspots.parquet (Silver layer from fuse_datasets.sql)
-- Output: data/processed/hotspots_harmonized.parquet
-- ==============================================================================

-- Step 1: Enrich Silver points with Local Solar Time (LST) and equal-area 0.02 deg grid
CREATE OR REPLACE TEMP TABLE base_points AS
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
FROM solar;

-- Step 2: Quadrant-hour co-occurrence summary
CREATE OR REPLACE TEMP TABLE quadrant_hourly AS
SELECT
    country,
    lat_q,
    lon_q,
    hour_window,
    count(*) FILTER (WHERE instrument = 'MODIS') AS modis_in_cluster,
    count(*) FILTER (WHERE instrument = 'VIIRS') AS viirs_in_cluster,
    sum(coalesce(frp, 0.0)) FILTER (WHERE instrument = 'MODIS') AS modis_frp_sum,
    sum(coalesce(frp, 0.0)) FILTER (WHERE instrument = 'VIIRS') AS viirs_frp_sum
FROM base_points
GROUP BY 1, 2, 3, 4;

-- Step 3: Empirical per-country calibration from the 2012+ overlap era
-- Falls back to Central America reference defaults (2.20, 6.12, 4.50, 1.14)
-- when a country has fewer than 100 Class A co-detection clusters.
CREATE OR REPLACE TEMP TABLE country_calibration AS
WITH class_a AS (
    SELECT
        country,
        count(*) AS class_a_clusters,
        sum(viirs_in_cluster)::DOUBLE / nullif(sum(modis_in_cluster), 0) AS raw_pixel_ratio,
        sum(viirs_frp_sum)::DOUBLE / nullif(sum(modis_frp_sum), 0) AS raw_frp_ratio
    FROM quadrant_hourly
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
    FROM base_points
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
  ON o.country = a.country;

-- Step 4: Assign point-level harmonization category, weight, and calibrated FRP
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
            WHEN b.instrument = 'MODIS' AND q.viirs_in_cluster > 0 THEN 'MODIS_REDUNDANT_CODETECTION'
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'MORNING_TERRA' THEN 'MODIS_UNIQUE_MORNING'
            WHEN b.instrument = 'MODIS' AND year(b.acq_datetime) < 2012 THEN 'MODIS_HISTORICAL_PRE_2012'
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'AFTERNOON_AQUA_VIIRS' THEN 'MODIS_SOLO_AFTERNOON'
            ELSE 'MODIS_SOLO_OTHER'
        END AS harmonization_category,
        CASE
            WHEN b.instrument = 'VIIRS' THEN 1.00
            WHEN b.instrument = 'MODIS' AND q.viirs_in_cluster > 0 THEN 0.00
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'MORNING_TERRA' THEN coalesce(c.f_morning, 2.20)
            WHEN b.instrument = 'MODIS' AND b.overpass_window = 'AFTERNOON_AQUA_VIIRS' THEN coalesce(c.f_afternoon, 6.12)
            ELSE coalesce(c.f_night, 4.50)
        END AS harmonized_weight,
        CASE
            WHEN b.instrument = 'VIIRS' THEN coalesce(b.frp, 0.0)
            WHEN b.instrument = 'MODIS' AND q.viirs_in_cluster > 0 THEN 0.00
            ELSE round(coalesce(b.frp, 0.0) * coalesce(c.f_frp, 1.14), 2)
        END AS harmonized_frp
    FROM base_points b
    JOIN quadrant_hourly q
      ON b.country = q.country
     AND b.lat_q = q.lat_q
     AND b.lon_q = q.lon_q
     AND b.hour_window = q.hour_window
    LEFT JOIN country_calibration c
      ON b.country = c.country
) TO 'data/processed/hotspots_harmonized.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
