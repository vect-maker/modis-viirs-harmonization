-- Enable PostGIS extension if not already enabled
CREATE EXTENSION IF NOT EXISTS postgis;

-- Hotspots table with native PostGIS Point geometry (WGS 84 / SRID 4326)
CREATE TABLE IF NOT EXISTS hotspots (
    id BIGINT PRIMARY KEY,
    country VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    bright_mir DOUBLE PRECISION,
    scan DOUBLE PRECISION,
    track DOUBLE PRECISION,
    acq_datetime TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    satellite VARCHAR(50),
    instrument VARCHAR(20) NOT NULL,
    confidence VARCHAR(20),
    confidence_class VARCHAR(20),
    version VARCHAR(20),
    bright_tir DOUBLE PRECISION,
    frp DOUBLE PRECISION,
    daynight VARCHAR(5),
    type INTEGER
);

-- Spatial and relational performance indexes
CREATE INDEX IF NOT EXISTS idx_hotspots_geom ON hotspots USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_hotspots_acq_datetime ON hotspots (acq_datetime);
CREATE INDEX IF NOT EXISTS idx_hotspots_country ON hotspots (country);
CREATE INDEX IF NOT EXISTS idx_hotspots_instrument ON hotspots (instrument);
CREATE INDEX IF NOT EXISTS idx_hotspots_country_dt ON hotspots (country, acq_datetime);
