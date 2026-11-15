-- Execution and memory optimizations
SET max_memory = '2GB';
SET temp_directory = 'data/temp/duckdb';
SET threads = 4;
SET preserve_insertion_order = false;

-- Base namespace UUID for FIRMS project (derived from DNS namespace + 'firms.nasa.gov')
-- In Python/RFC 4122: uuid.uuid5(uuid.NAMESPACE_DNS, 'firms.nasa.gov')
-- = '98b00dc4-63e7-5855-bfed-2cdc66170e68'
CREATE OR REPLACE MACRO uuid5(ns_str, name_str) AS (
    WITH h AS (
        SELECT sha1(from_hex(replace(ns_str, '-', '')) || name_str::BLOB) AS s
    )
    SELECT (
        substring(s, 1, 8) || '-' ||
        substring(s, 9, 4) || '-' ||
        '5' || substring(s, 14, 3) || '-' ||
        lower(printf('%02x', ('0x' || substring(s, 17, 2))::INT & 63 | 128)) || substring(s, 19, 2) || '-' ||
        substring(s, 21, 12)
    )::UUID
    FROM h
);

CREATE OR REPLACE MACRO firms_uuid5(name_str) AS (
    uuid5('98b00dc4-63e7-5855-bfed-2cdc66170e68', name_str)
);

-- ============================================================================
-- 1. Country Dimension (dim_country)
-- ============================================================================
COPY (
    SELECT DISTINCT
        firms_uuid5('country:' || lower(trim(country))) AS id,
        trim(country) AS name
    FROM read_parquet('data/processed/hotspots_harmonized.parquet')
    WHERE country IS NOT NULL
    ORDER BY name
) TO 'data/processed/star/dim_country.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);

-- ============================================================================
-- 2. Platform Dimension (dim_platform)
-- ============================================================================
COPY (
    SELECT DISTINCT
        firms_uuid5('platform:' || lower(trim(satellite)) || ':' || lower(trim(instrument))) AS id,
        trim(satellite) AS satellite,
        trim(instrument) AS instrument
    FROM read_parquet('data/processed/hotspots_harmonized.parquet')
    WHERE satellite IS NOT NULL AND instrument IS NOT NULL
    ORDER BY instrument, satellite
) TO 'data/processed/star/dim_platform.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);

-- ============================================================================
-- 3. Hotspots Fact Table (fact_hotspots)
-- ============================================================================
COPY (
    SELECT DISTINCT ON (id)
        firms_uuid5(
            'detection:' ||
            round(latitude, 5)::VARCHAR || ':' ||
            round(longitude, 5)::VARCHAR || ':' ||
            strftime(acq_datetime, '%Y-%m-%dT%H:%M:%S') || ':' ||
            lower(trim(satellite)) || ':' ||
            lower(trim(instrument))
        ) AS id,
        firms_uuid5('country:' || lower(trim(country))) AS country_id,
        firms_uuid5('platform:' || lower(trim(satellite)) || ':' || lower(trim(instrument))) AS platform_id,
        latitude,
        longitude,
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
        version,
        overpass_window,
        harmonization_category,
        harmonized_weight,
        harmonized_frp
    FROM read_parquet('data/processed/hotspots_harmonized.parquet')
) TO 'data/processed/star/fact_hotspots.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
