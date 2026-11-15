-- Execution settings
SET max_memory = '10GB';
SET threads = 8;

-- Load required DuckDB extensions
LOAD postgres;
LOAD spatial;

.print 'Connecting to PostgreSQL/PostGIS database via DATABASE_URL...'
-- pg is attached via -cmd in justfile using $DATABASE_URL

.print 'Clearing existing cluster data from tables...'
TRUNCATE pg.clusterhotspots;
TRUNCATE pg.firecluster;

.print 'Loading firecluster from data/clusters/fire_clusters.parquet...'
.timer on

INSERT INTO pg.firecluster (
    id,
    polygon,
    status,
    "datetimeStart",
    "datetimeEnd",
    "maxFrp",
    centroid,
    geom,
    area_km2,
    centroid_lat,
    centroid_lon,
    hotspot_count,
    modis_count,
    viirs_count,
    total_frp,
    harmonized_weight
)
SELECT
    cluster_id AS id,
    COALESCE(area_km2, 0.0) AS polygon,
    CASE
        WHEN datetime_end >= CURRENT_TIMESTAMP - INTERVAL '24 hours' THEN 'ACTIVO'
        WHEN hotspot_count = 1 THEN 'AISLADO'
        ELSE 'FINALIZADO'
    END AS status,
    datetime_start AS "datetimeStart",
    datetime_end AS "datetimeEnd",
    max_frp AS "maxFrp",
    ST_GeomFromText(centroid_wkt) AS centroid,
    ST_GeomFromText(geom_wkt) AS geom,
    COALESCE(area_km2, 0.0) AS area_km2,
    centroid_lat,
    centroid_lon,
    hotspot_count,
    modis_count,
    viirs_count,
    total_frp,
    harmonized_weight
FROM read_parquet('data/clusters/fire_clusters.parquet');

.print 'Loading clusterhotspots from data/clusters/cluster_hotspots.parquet...'

INSERT INTO pg.clusterhotspots (
    "clusterId",
    "hotspotsId"
)
SELECT
    cluster_id AS "clusterId",
    hotspot_id AS "hotspotsId"
FROM read_parquet('data/clusters/cluster_hotspots.parquet');

.print 'Cluster ingestion into PostgreSQL completed successfully!'
