-- Execution and memory optimizations
SET max_memory = '10GB';
SET temp_directory = 'data/temp/duckdb';
SET threads = 8;
SET preserve_insertion_order = false;

-- Enable live progress reporting in terminal
SET enable_progress_bar = true;
SET progress_bar_time = 500;

-- Pre-materialize completed files to avoid repeated SQLite table scans during parallel reading
-- Scope defaults to 'central_america' for fast local development; set fuse_scope = 'all' for global runs
CREATE OR REPLACE TEMP TABLE completed_files AS
SELECT local_path, country
FROM sqlite_scan('data/pipeline.db', 'archive_files')
WHERE status = 'completed'
  AND (
      coalesce(getvariable('fuse_scope'), 'central_america') = 'all'
      OR country IN (
          'Belize',
          'Costa_Rica',
          'El_Salvador',
          'Guatemala',
          'Honduras',
          'Nicaragua',
          'Panama'
      )
  );

-- Consolidate MODIS and VIIRS archive datasets into a unified Silver dataset
COPY (
    -- 1. MODIS Hotspots
    SELECT
        f.country,
        p.latitude,
        p.longitude,
        p.brightness AS bright_mir,
        p.scan,
        p.track,
        strptime(p.acq_date || ' ' || p.acq_time, '%Y-%m-%d %H%M')::TIMESTAMP AS acq_datetime,
        p.satellite,
        p.instrument,
        try_cast(p.confidence AS INTEGER) AS confidence,
        CASE
            WHEN try_cast(p.confidence AS INTEGER) < 30 THEN 'l'
            WHEN try_cast(p.confidence AS INTEGER) < 80 THEN 'n'
            ELSE 'h'
        END AS confidence_class,
        p.version,
        p.bright_t31 AS bright_tir,
        p.frp,
        p.daynight,
        p.type::INTEGER AS type
    FROM read_parquet('data/raw/modis/*/*.parquet', filename=true) p
    JOIN completed_files f
      ON p.filename = f.local_path

    UNION ALL

    -- 2. VIIRS Hotspots
    SELECT
        f.country,
        p.latitude,
        p.longitude,
        p.bright_ti4 AS bright_mir,
        p.scan,
        p.track,
        strptime(p.acq_date || ' ' || p.acq_time, '%Y-%m-%d %H%M')::TIMESTAMP AS acq_datetime,
        CASE p.satellite
            WHEN 'N' THEN 'Suomi-NPP'
            WHEN 'N20' THEN 'NOAA-20'
            WHEN 'N21' THEN 'NOAA-21'
            ELSE p.satellite
        END AS satellite,
        p.instrument,
        CASE lower(p.confidence)
            WHEN 'l' THEN 20
            WHEN 'n' THEN 50
            WHEN 'h' THEN 90
            ELSE NULL
        END::INTEGER AS confidence,
        lower(p.confidence) AS confidence_class,
        p.version,
        p.bright_ti5 AS bright_tir,
        p.frp,
        p.daynight,
        p.type::INTEGER AS type
    FROM read_parquet('data/raw/viirs*/*/*.parquet', filename=true) p
    JOIN completed_files f
      ON p.filename = f.local_path
) TO 'data/processed/hotspots.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
