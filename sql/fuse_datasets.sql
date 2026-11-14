-- 1. MODIS consolidated dataset
COPY (
    SELECT
        f.country,
        p.* EXCLUDE (filename)
    FROM read_parquet('data/raw/modis/*/*.parquet', filename=true) p
    JOIN sqlite_scan('data/pipeline.db', 'archive_files') f
      ON p.filename = f.local_path
    WHERE f.status = 'completed'
    ORDER BY f.country, p.acq_date, p.acq_time
) TO 'data/processed/modis.parquet' (FORMAT PARQUET, COMPRESSION SNAPPY);

-- 2. VIIRS consolidated dataset
COPY (
    SELECT
        f.country,
        p.latitude,
        p.longitude,
        p.bright_ti4,
        p.scan,
        p.track,
        p.acq_date,
        p.acq_time,
        CASE p.satellite
            WHEN 'N' THEN 'Suomi-NPP'
            WHEN 'N20' THEN 'NOAA-20'
            WHEN 'N21' THEN 'NOAA-21'
            ELSE p.satellite
        END AS satellite,
        p.instrument,
        p.confidence,
        p.version,
        p.bright_ti5,
        p.frp,
        p.daynight,
        p.type
    FROM read_parquet('data/raw/viirs*/*/*.parquet', filename=true) p
    JOIN sqlite_scan('data/pipeline.db', 'archive_files') f
      ON p.filename = f.local_path
    WHERE f.status = 'completed'
    ORDER BY f.country, p.acq_date, p.acq_time
) TO 'data/processed/viirs.parquet' (FORMAT PARQUET, COMPRESSION SNAPPY);
