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
        f.instrument as viirs_instrument,
        p.* EXCLUDE (filename)
    FROM read_parquet('data/raw/viirs*/*/*.parquet', filename=true) p
    JOIN sqlite_scan('data/pipeline.db', 'archive_files') f
      ON p.filename = f.local_path
    WHERE f.status = 'completed'
    ORDER BY f.country, p.acq_date, p.acq_time
) TO 'data/processed/viirs.parquet' (FORMAT PARQUET, COMPRESSION SNAPPY);
