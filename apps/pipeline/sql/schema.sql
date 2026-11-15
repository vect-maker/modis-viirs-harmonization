-- Schema definition for FIRMS active fire hotspots (Star Schema) & Clustering/Environmental models.
-- Executed directly against the target database (firms) via DATABASE_URL.

-- Drop existing views, tables, and types if rebuilding schema
DROP VIEW IF EXISTS hotspots CASCADE;
DROP TABLE IF EXISTS hotspots CASCADE;
DROP TABLE IF EXISTS clusterhotspots CASCADE;
DROP TABLE IF EXISTS environmentalrecord CASCADE;
DROP TABLE IF EXISTS firecluster CASCADE;
DROP TYPE IF EXISTS clusterstatus CASCADE;
DROP TABLE IF EXISTS fact_hotspots CASCADE;
DROP TABLE IF EXISTS dim_platform CASCADE;
DROP TABLE IF EXISTS dim_country CASCADE;

-- ============================================================================
-- 1. Country Dimension
-- Primary Key: UUIDv5 seeded on 'country:' || lower(trim(name))
-- ============================================================================
CREATE TABLE dim_country (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- ============================================================================
-- 2. Platform / Sensor Dimension (MODIS & VIIRS satellite payloads)
-- Primary Key: UUIDv5 seeded on 'platform:' || lower(trim(satellite)) || ':' || lower(trim(instrument))
-- ============================================================================
CREATE TABLE dim_platform (
    id UUID PRIMARY KEY,
    satellite VARCHAR(50) NOT NULL,
    instrument VARCHAR(20) NOT NULL,
    CONSTRAINT uq_platform UNIQUE (satellite, instrument)
);

-- ============================================================================
-- 3. Hotspots Fact Table (Active Fire Observations)
-- Primary Key: UUIDv5 seeded on 'detection:' || latitude || ':' || longitude || ':' || to_char(acq_datetime, 'YYYY-MM-DD"T"HH24:MI:SS') || ':' || lower(trim(satellite)) || ':' || lower(trim(instrument))
-- ============================================================================
CREATE TABLE fact_hotspots (
    id UUID PRIMARY KEY,
    country_id UUID NOT NULL REFERENCES dim_country (id),
    platform_id UUID NOT NULL REFERENCES dim_platform (id),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    acq_datetime TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    bright_mir DOUBLE PRECISION,
    bright_tir DOUBLE PRECISION,
    scan DOUBLE PRECISION,
    track DOUBLE PRECISION,
    confidence INTEGER,
    confidence_class VARCHAR(20),
    frp DOUBLE PRECISION,
    daynight VARCHAR(5),
    type INTEGER,
    version VARCHAR(20),
    overpass_window VARCHAR(30),
    harmonization_category VARCHAR(40),
    harmonized_weight DOUBLE PRECISION,
    harmonized_frp DOUBLE PRECISION
);

-- Spatial and relational performance indexes
CREATE INDEX idx_fact_hotspots_geom ON fact_hotspots USING GIST (geom);
CREATE INDEX idx_fact_hotspots_acq_datetime ON fact_hotspots (acq_datetime);
CREATE INDEX idx_fact_hotspots_country_dt ON fact_hotspots (country_id, acq_datetime);
CREATE INDEX idx_fact_hotspots_platform ON fact_hotspots (platform_id);

-- ============================================================================
-- 4. Backward-Compatible Hotspots View
-- Recreates the exact denormalized table structure for existing queries & GIS tools
-- ============================================================================
CREATE OR REPLACE VIEW hotspots AS
SELECT
    f.id,
    c.name AS country,
    f.latitude,
    f.longitude,
    f.geom,
    f.bright_mir,
    f.scan,
    f.track,
    f.acq_datetime,
    p.satellite,
    p.instrument,
    f.confidence,
    f.confidence_class,
    f.version,
    f.bright_tir,
    f.frp,
    f.daynight,
    f.type,
    f.overpass_window,
    f.harmonization_category,
    f.harmonized_weight,
    f.harmonized_frp
FROM fact_hotspots f
JOIN dim_country c ON f.country_id = c.id
JOIN dim_platform p ON f.platform_id = p.id;

-- ============================================================================
-- 5. Fire Clusters & Environmental Records (Backend / Analytics Models)
-- ============================================================================
CREATE TYPE clusterstatus AS ENUM ('ACTIVO', 'AISLADO', 'FINALIZADO');

CREATE TABLE firecluster (
    id SERIAL PRIMARY KEY,
    polygon DOUBLE PRECISION NOT NULL,
    status clusterstatus NOT NULL DEFAULT 'ACTIVO',
    "datetimeStart" TIMESTAMP WITH TIME ZONE,
    "datetimeEnd" TIMESTAMP WITH TIME ZONE,
    "maxFrp" DOUBLE PRECISION,
    "dirExpansion" DOUBLE PRECISION,
    "veloExpansion" DOUBLE PRECISION
);

CREATE INDEX idx_firecluster_status ON firecluster (status);
CREATE INDEX idx_firecluster_datetime ON firecluster ("datetimeStart", "datetimeEnd");

CREATE TABLE clusterhotspots (
    "clusterId" INTEGER NOT NULL REFERENCES firecluster (id) ON DELETE CASCADE,
    "hotspotsId" INTEGER NOT NULL,
    PRIMARY KEY ("clusterId", "hotspotsId")
);

CREATE INDEX idx_clusterhotspots_hotspot ON clusterhotspots ("hotspotsId");

CREATE TABLE environmentalrecord (
    id SERIAL PRIMARY KEY,
    "datetimeStart" TIMESTAMP WITH TIME ZONE,
    humidity DOUBLE PRECISION,
    precipitation DOUBLE PRECISION,
    temperature DOUBLE PRECISION,
    "windSpeed" DOUBLE PRECISION,
    "windDirection" DOUBLE PRECISION,
    "vegetationType" DOUBLE PRECISION,
    "densityVegetation" DOUBLE PRECISION,
    nubosity DOUBLE PRECISION,
    "fireClusterId" INTEGER REFERENCES firecluster (id) ON DELETE SET NULL
);

CREATE INDEX idx_environmentalrecord_cluster ON environmentalrecord ("fireClusterId");
