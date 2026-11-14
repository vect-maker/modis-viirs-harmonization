-- Execution settings
SET max_memory = '10GB';
SET threads = 8;

-- Load required DuckDB extensions
LOAD postgres;
LOAD spatial;

.print 'Connecting to PostgreSQL/PostGIS database via DATABASE_URL...'
ATTACH getenv('DATABASE_URL') AS pg (TYPE POSTGRES);

.print 'Clearing existing data from hotspots table...'
TRUNCATE pg.hotspots;

.print 'Streaming Nicaragua hotspots from data/processed/hotspots.parquet...'
.timer on

INSERT INTO pg.hotspots
SELECT
    row_number() OVER () AS id,
    country,
    latitude,
    longitude,
    ST_Point(longitude, latitude) AS geom,
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
    type
FROM read_parquet('data/processed/hotspots.parquet')
WHERE country = 'Nicaragua';

.print 'Data ingestion into PostgreSQL completed successfully!'
