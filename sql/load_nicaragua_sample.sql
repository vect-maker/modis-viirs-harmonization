-- Execution settings
SET max_memory = '10GB';
SET threads = 8;

-- Load required DuckDB extensions
LOAD postgres;
LOAD spatial;

.print 'Connecting to PostgreSQL/PostGIS database via DATABASE_URL...'
ATTACH getenv('DATABASE_URL') AS pg (TYPE POSTGRES);

.print 'Clearing existing data from tables...'
TRUNCATE pg.fact_hotspots;
TRUNCATE pg.dim_platform;
TRUNCATE pg.dim_country;

.print 'Loading dim_country from data/processed/star/dim_country.parquet...'
INSERT INTO pg.dim_country
SELECT id, name
FROM read_parquet('data/processed/star/dim_country.parquet');

.print 'Loading dim_platform from data/processed/star/dim_platform.parquet...'
INSERT INTO pg.dim_platform
SELECT id, satellite, instrument
FROM read_parquet('data/processed/star/dim_platform.parquet');

.print 'Streaming fact_hotspots from data/processed/star/fact_hotspots.parquet...'
.timer on

INSERT INTO pg.fact_hotspots
SELECT
    id,
    country_id,
    platform_id,
    latitude,
    longitude,
    ST_Point(longitude, latitude) AS geom,
    acq_datetime,
    bright_mir,
    bright_tir,
    scan,
    track,
    confidence,
    confidence_class,
    frp,
    daynight,
    type,
    version
FROM read_parquet('data/processed/star/fact_hotspots.parquet');

.print 'Data ingestion into PostgreSQL completed successfully!'
