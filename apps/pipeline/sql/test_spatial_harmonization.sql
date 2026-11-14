-- Execution and memory optimizations
SET max_memory = '10GB';
SET threads = 8;
LOAD spatial;

-- ==============================================================================
-- BENCHMARK 1: Regional Extraction (Chilecito / La Rioja, Argentina)
-- Preserving Point-Level Grain (Exact Lat, Lon, Datetime, FRP)
-- ==============================================================================
.print ''
.print '=== BENCHMARK 1: Point-Level Spatial Extraction (Chilecito ROI) ==='
.timer on

CREATE OR REPLACE TEMP TABLE roi_points AS
SELECT
    country,
    satellite,
    instrument,
    latitude,
    longitude,
    acq_datetime,
    frp,
    confidence,
    -- Spatio-temporal quadrant coordinates (approx 2 km grid)
    round(latitude, 2) AS lat_q,
    round(longitude, 2) AS lon_q,
    -- Hourly overpass bucket
    date_trunc('hour', acq_datetime) AS hour_window,
    -- Solar overpass pass type (UTC -3 approximation for Argentina)
    CASE 
        WHEN hour(acq_datetime) BETWEEN 12 AND 15 THEN 'Morning Pass (Terra)'
        WHEN hour(acq_datetime) BETWEEN 16 AND 20 THEN 'Afternoon Pass (Aqua + VIIRS)'
        ELSE 'Night / Off-Cycle Pass'
    END AS overpass_window
FROM read_parquet('data/processed/hotspots.parquet')
WHERE country = 'Argentina'
  AND ST_Within(
      ST_Point(longitude, latitude),
      ST_GeomFromText('POLYGON((-68.2 -29.8, -66.8 -29.8, -66.8 -28.5, -68.2 -28.5, -68.2 -29.8))')
  );

SELECT 
    instrument, 
    count(*) AS total_points, 
    min(acq_datetime) AS earliest_record,
    max(acq_datetime) AS latest_record,
    round(min(frp), 2) AS min_frp_mw, 
    round(avg(frp), 2) AS avg_frp_mw, 
    round(max(frp), 2) AS max_frp_mw
FROM roi_points
GROUP BY instrument;

-- ==============================================================================
-- BENCHMARK 2: Hourly Quadrant Co-occurrence & Anomaly Categorization
-- Identifies which satellites had readings in the same quadrant at the same hour
-- ==============================================================================
.print ''
.print '=== BENCHMARK 2: Hourly Quadrant Co-occurrence & Anomaly Classification ==='

CREATE OR REPLACE TEMP TABLE quadrant_hourly_summary AS
SELECT
    lat_q,
    lon_q,
    hour_window,
    overpass_window,
    count(CASE WHEN instrument = 'MODIS' THEN 1 END) AS modis_count,
    count(CASE WHEN instrument = 'VIIRS' THEN 1 END) AS viirs_count,
    round(sum(CASE WHEN instrument = 'MODIS' THEN coalesce(frp, 0) ELSE 0 END), 1) AS modis_frp_total,
    round(sum(CASE WHEN instrument = 'VIIRS' THEN coalesce(frp, 0) ELSE 0 END), 1) AS viirs_frp_total,
    string_agg(DISTINCT satellite, ', ') AS satellites_present
FROM roi_points
GROUP BY 1, 2, 3, 4;

CREATE OR REPLACE TEMP TABLE quadrant_classified AS
SELECT
    *,
    CASE 
        -- 1. Simultaneous Co-detection: Both sensors caught the fire at the same hour
        WHEN modis_count > 0 AND viirs_count > 0 
            THEN 'A: Simultaneous Co-Detection (Same Hour & Quadrant)'
        -- 2. Sensitivity Gap: Afternoon pass, but MODIS missed it (faint fire)
        WHEN modis_count = 0 AND viirs_count > 0 AND overpass_window = 'Afternoon Pass (Aqua + VIIRS)'
            THEN 'B: VIIRS Afternoon Faint/Solo Fire (MODIS Missed)'
        -- 3. Diurnal Difference: Morning burn detected by Terra (VIIRS has no 10:30 AM pass)
        WHEN modis_count > 0 AND viirs_count = 0 AND overpass_window = 'Morning Pass (Terra)'
            THEN 'C: Terra Morning Solo Fire (Diurnal Cycle)'
        -- 4. Overnight / Off-cycle burns
        WHEN modis_count = 0 AND viirs_count > 0 
            THEN 'D: VIIRS Night/Off-Cycle Fire'
        ELSE 'E: MODIS Other Solo Fire'
    END AS anomaly_classification
FROM quadrant_hourly_summary;

SELECT 
    anomaly_classification,
    count(*) AS total_quadrant_hours,
    sum(modis_count) AS modis_pts,
    sum(viirs_count) AS viirs_pts,
    round(avg(CASE WHEN modis_count > 0 AND viirs_count > 0 THEN viirs_count::DOUBLE / modis_count END), 2) AS co_detection_pixel_ratio,
    round(avg(CASE WHEN viirs_count > 0 THEN viirs_frp_total END), 1) AS avg_viirs_frp_mw,
    round(avg(CASE WHEN modis_count > 0 THEN modis_frp_total END), 1) AS avg_modis_frp_mw
FROM quadrant_classified
GROUP BY 1
ORDER BY 1;

-- ==============================================================================
-- BENCHMARK 3: Direct Sensor Comparison in Simultaneous Co-Detections
-- When both Aqua & VIIRS pass over the exact same quadrant at the same hour
-- ==============================================================================
.print ''
.print '=== BENCHMARK 3: Direct Co-Detections at the Exact Same Hour (Sample Detections) ==='

SELECT 
    hour_window,
    lat_q,
    lon_q,
    satellites_present,
    modis_count,
    viirs_count,
    round(viirs_count::DOUBLE / modis_count, 1) AS viirs_to_modis_ratio,
    modis_frp_total,
    viirs_frp_total
FROM quadrant_classified
WHERE anomaly_classification LIKE 'A:%'
ORDER BY viirs_count DESC
LIMIT 10;

-- ==============================================================================
-- BENCHMARK 4: Enriched Point-Level Output (Retaining 100% of Data Grain)
-- Every individual fire point is preserved with its granular anomaly context
-- ==============================================================================
.print ''
.print '=== BENCHMARK 4: Enriched Point-Level Hotspots (No Grain Loss) ==='

SELECT 
    p.acq_datetime,
    p.satellite,
    p.instrument,
    p.latitude,
    p.longitude,
    p.frp,
    q.anomaly_classification,
    -- Point-level harmonized weight without discarding coordinates or time!
    CASE 
        WHEN p.instrument = 'VIIRS' THEN 1.0
        WHEN p.instrument = 'MODIS' AND q.anomaly_classification LIKE 'A:%' 
            THEN round(q.viirs_count::DOUBLE / q.modis_count, 1)
        ELSE 2.25 -- Average direct footprint multiplicity
    END AS point_harmonized_viirs_weight
FROM roi_points p
JOIN quadrant_classified q
  ON p.lat_q = q.lat_q 
 AND p.lon_q = q.lon_q 
 AND p.hour_window = q.hour_window
ORDER BY p.acq_datetime DESC
LIMIT 10;
