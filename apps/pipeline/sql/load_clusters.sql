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
TRUNCATE pg.firecluster CASCADE;

.print 'Loading firecluster from data/clusters/fire_clusters.parquet...'
.timer on

INSERT INTO pg.firecluster (
    id,
    polygon,
    status,
    "datetimeStart",
    "datetimeEnd",
    "maxFrp"
)
SELECT
    cluster_id                 AS id,
    COALESCE(area_km2, 0.0)    AS polygon,
    'ACTIVO'                   AS status,
    datetime_start             AS "datetimeStart",
    datetime_end               AS "datetimeEnd",
    max_frp                    AS "maxFrp"
FROM read_parquet('data/clusters/fire_clusters.parquet');

.print 'Loading clusterhotspots from data/clusters/cluster_hotspots.parquet...'

INSERT INTO pg.clusterhotspots (
    "clusterId",
    "hotspotsId"
)
SELECT
    cluster_id                 AS "clusterId",
    hs_id                      AS "hotspotsId"
FROM read_parquet('data/clusters/cluster_hotspots.parquet');

.print 'Cluster ingestion into PostgreSQL completed successfully!'
