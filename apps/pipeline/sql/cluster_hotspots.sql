-- =============================================================================
-- cluster_hotspots.sql
-- Clusterización espaciotemporal de hotspots FIRMS con DuckDB SQL puro.
--
-- Parámetros de clustering:
--   · Radio   : ~1 km  -> grilla de 0.009° (aprox. 1 km en latitud)
--   · Ventana : 24 h   -> slot = FLOOR(epoch(acq_datetime) / 86400)
--
-- Entrada  : data/raw/**/*.parquet
-- Salida   : data/clusters/fire_clusters.parquet
--            data/clusters/cluster_hotspots.parquet
--
-- Ejecutar desde apps/pipeline/:
--   duckdb < sql/cluster_hotspots.sql
-- =============================================================================

-- =============================================================================
-- STEP 1 · Parsear fecha/hora y normalizar atributos desde Parquet
-- =============================================================================
CREATE OR REPLACE VIEW v_raw_hotspots AS
SELECT
    latitude,
    longitude,
    TRY_CAST(frp AS DOUBLE)                                     AS frp,
    COALESCE(
        TRY_CAST(bright_ti5 AS DOUBLE),
        TRY_CAST(bright_t31 AS DOUBLE)
    )                                                           AS bright_tir,
    COALESCE(
        TRY_CAST(bright_ti4 AS DOUBLE),
        TRY_CAST(brightness AS DOUBLE)
    )                                                           AS bright_mir,
    TRY_CAST(scan AS DOUBLE)                                    AS scan,
    TRY_CAST(track AS DOUBLE)                                   AS track,
    CAST(satellite AS VARCHAR)                                  AS satellite,
    CAST(instrument AS VARCHAR)                                 AS instrument,
    CAST(confidence AS VARCHAR)                                 AS confidence,
    CAST(daynight AS VARCHAR)                                   AS daynight,
    TRY_STRPTIME(
        CONCAT(
            CAST(acq_date AS VARCHAR),
            ' ',
            LPAD(CAST(acq_time AS VARCHAR), 4, '0')
        ),
        '%Y-%m-%d %H%M'
    )                                                           AS acq_datetime
FROM read_parquet(
    'data/raw/**/*.parquet',
    union_by_name     = true,
    hive_partitioning = false
);


-- =============================================================================
-- STEP 2 · Filtrar datos válidos y generar ID secuencial ordenado
-- =============================================================================
CREATE OR REPLACE VIEW v_hotspots AS
SELECT
    ROW_NUMBER() OVER (ORDER BY acq_datetime ASC) - 1           AS hs_id,
    latitude,
    longitude,
    acq_datetime,
    frp,
    bright_tir,
    bright_mir,
    scan,
    track,
    satellite,
    instrument,
    confidence,
    daynight
FROM v_raw_hotspots
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
  AND acq_datetime IS NOT NULL;


-- =============================================================================
-- STEP 3 · Asignar celda de grilla espaciotemporal (~1 km x 1 km, ventana 24h)
-- =============================================================================
-- 0.009° en latitud equivale aproximadamente a 1.002 km.
-- 86400 segundos equivalen a 24 horas (un día Unix UTC).
CREATE OR REPLACE VIEW v_gridded AS
SELECT
    *,
    ROUND(latitude / 0.009)               AS grid_lat,
    ROUND(longitude / 0.009)              AS grid_lon,
    FLOOR(EPOCH(acq_datetime) / 86400.0)  AS time_slot
FROM v_hotspots;


-- =============================================================================
-- STEP 4 · Generar cluster_id con DENSE_RANK
-- =============================================================================
CREATE OR REPLACE VIEW v_assigned AS
SELECT
    *,
    DENSE_RANK() OVER (
        ORDER BY grid_lat, grid_lon, time_slot
    ) - 1                                 AS cluster_id
FROM v_gridded;


-- =============================================================================
-- STEP 5 · Calcular estadísticas por cluster
-- =============================================================================
CREATE OR REPLACE VIEW v_cluster_stats AS
SELECT
    cluster_id,
    COUNT(*)                                                AS hotspot_count,
    ROUND(AVG(latitude), 6)                                 AS centroid_lat,
    ROUND(AVG(longitude), 6)                                AS centroid_lon,
    MIN(acq_datetime)                                       AS datetime_start,
    MAX(acq_datetime)                                       AS datetime_end,
    ROUND(
        (EPOCH(MAX(acq_datetime)) - EPOCH(MIN(acq_datetime))) / 3600.0,
        2
    )                                                       AS duration_h,
    ROUND(MAX(frp), 4)                                      AS max_frp,
    ROUND(AVG(frp), 4)                                      AS avg_frp,
    ROUND(
          (MAX(latitude) - MIN(latitude)) * 111.32
        * (MAX(longitude) - MIN(longitude)) * 111.32
        * COS(RADIANS(AVG(latitude))),
        4
    )                                                       AS area_km2,
    'Activo'                                                AS status
FROM v_assigned
GROUP BY cluster_id;


-- =============================================================================
-- STEP 6a · Guardar fire_clusters.parquet (un registro por cluster)
-- =============================================================================
COPY (
    SELECT
        cluster_id,
        hotspot_count,
        centroid_lat,
        centroid_lon,
        datetime_start,
        datetime_end,
        duration_h,
        max_frp,
        avg_frp,
        area_km2,
        status
    FROM v_cluster_stats
    ORDER BY cluster_id
)
TO 'data/clusters/fire_clusters.parquet' (
    FORMAT      PARQUET,
    COMPRESSION SNAPPY
);


-- =============================================================================
-- STEP 6b · Guardar cluster_hotspots.parquet (relación hotspot -> cluster_id)
-- =============================================================================
COPY (
    SELECT
        hs_id,
        cluster_id,
        latitude,
        longitude,
        acq_datetime,
        ROUND(frp, 4)         AS frp,
        ROUND(bright_tir, 4)  AS bright_tir,
        ROUND(bright_mir, 4)  AS bright_mir,
        ROUND(scan, 4)        AS scan,
        ROUND(track, 4)       AS track,
        satellite,
        instrument,
        confidence,
        daynight
    FROM v_assigned
    ORDER BY cluster_id, acq_datetime
)
TO 'data/clusters/cluster_hotspots.parquet' (
    FORMAT      PARQUET,
    COMPRESSION SNAPPY
);


-- =============================================================================
-- STEP 7 · Mostrar resumen
-- =============================================================================
SELECT
    COUNT(DISTINCT cluster_id)  AS total_clusters,
    COUNT(*)                    AS total_hotspots,
    MIN(acq_datetime)           AS period_start,
    MAX(acq_datetime)           AS period_end,
    ROUND(AVG(frp), 2)          AS avg_frp_global,
    ROUND(MAX(frp), 2)          AS max_frp_global
FROM v_assigned;
