-- =============================================================================
-- 01_assign_events.sql
-- Pure DuckDB SQL spatio-temporal Fire Event assignment:
--   - Spatial cell: 0.02° (~2.2 km)
--   - Temporal continuity: splits only when gap > 24 hours (86400 s)
--     between consecutive detections in the same cell (no UTC-midnight split).
--
-- Input  : data/processed/star/fact_hotspots.parquet
--          data/processed/star/dim_platform.parquet
-- Output : data/temp/clusters/assigned_hotspots.parquet
-- =============================================================================

SET max_memory = '10GB';
SET threads = 8;

COPY (
    WITH base AS (
        SELECT
            f.id AS hotspot_id,
            f.latitude,
            f.longitude,
            f.acq_datetime,
            f.frp,
            f.harmonized_weight,
            UPPER(p.instrument) AS instrument,
            ROUND(f.latitude / 0.02)::BIGINT AS grid_lat,
            ROUND(f.longitude / 0.02)::BIGINT AS grid_lon
        FROM read_parquet('data/processed/star/fact_hotspots.parquet') f
        JOIN read_parquet('data/processed/star/dim_platform.parquet') p
          ON f.platform_id = p.id
        WHERE f.latitude IS NOT NULL
          AND f.longitude IS NOT NULL
          AND f.acq_datetime IS NOT NULL
    ),
    with_prev AS (
        SELECT
            *,
            LAG(acq_datetime) OVER (
                PARTITION BY grid_lat, grid_lon
                ORDER BY acq_datetime, hotspot_id
            ) AS prev_dt
        FROM base
    ),
    flagged AS (
        SELECT
            *,
            CASE
                WHEN prev_dt IS NULL
                  OR (EPOCH(acq_datetime) - EPOCH(prev_dt)) > 86400.0
                THEN 1
                ELSE 0
            END AS is_new_event
        FROM with_prev
    ),
    sequenced AS (
        SELECT
            *,
            SUM(is_new_event) OVER (
                PARTITION BY grid_lat, grid_lon
                ORDER BY acq_datetime, hotspot_id
            ) AS event_seq
        FROM flagged
    )
    SELECT
        DENSE_RANK() OVER (
            ORDER BY grid_lat, grid_lon, event_seq
        )::INTEGER AS cluster_id,
        hotspot_id,
        latitude,
        longitude,
        acq_datetime,
        frp,
        harmonized_weight,
        instrument
    FROM sequenced
) TO 'data/temp/clusters/assigned_hotspots.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
