-- 1. MODIS consolidated dataset
COPY (
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
        p.confidence,
        CASE
            WHEN p.confidence::BIGINT < 30 THEN 'l'
            WHEN p.confidence::BIGINT < 80 THEN 'n'
            ELSE 'h'
        END AS confidence_class,
        p.version,
        p.bright_t31 AS bright_tir,
        p.frp,
        p.daynight,
        p.type::INTEGER AS type
    FROM read_parquet('data/raw/modis/*/*.parquet', filename=true) p
    JOIN sqlite_scan('data/pipeline.db', 'archive_files') f
      ON p.filename = f.local_path
    WHERE f.status = 'completed'
    ORDER BY f.country, acq_datetime
) TO 'data/processed/modis.parquet' (FORMAT PARQUET, COMPRESSION SNAPPY);

-- 2. VIIRS consolidated dataset
COPY (
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
        p.confidence,
        p.confidence AS confidence_class,
        p.version,
        p.bright_ti5 AS bright_tir,
        p.frp,
        p.daynight,
        p.type::INTEGER AS type
    FROM read_parquet('data/raw/viirs*/*/*.parquet', filename=true) p
    JOIN sqlite_scan('data/pipeline.db', 'archive_files') f
      ON p.filename = f.local_path
    WHERE f.status = 'completed'
    ORDER BY f.country, acq_datetime
) TO 'data/processed/viirs.parquet' (FORMAT PARQUET, COMPRESSION SNAPPY);
