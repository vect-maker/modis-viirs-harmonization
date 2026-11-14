-- Run from apps/pipeline. Override source_path with DuckDB SET VARIABLE when needed.
-- Raw detection aggregates only: no harmonization or observation-coverage claims.
COPY (
  WITH source AS (
    SELECT * FROM read_parquet(coalesce(getvariable('source_path'), 'data/processed/hotspots.parquet'))
    WHERE lower(trim(country)) = 'nicaragua'
  ), monthly AS (
    SELECT
      year(acq_datetime)::INTEGER AS year,
      month(acq_datetime)::INTEGER AS month,
      count(*)::INTEGER AS total,
      nullif(count(*) FILTER (WHERE instrument = 'MODIS'), 0)::INTEGER AS modisCount,
      nullif(count(*) FILTER (WHERE instrument = 'VIIRS'), 0)::INTEGER AS viirsCount,
      count(DISTINCT acq_datetime::DATE)::INTEGER AS observedDays,
      round(avg(frp), 2) AS avgFrp,
      strftime(min(acq_datetime), '%Y-%m-%d %H:%M:%S') AS firstDetection,
      strftime(max(acq_datetime), '%Y-%m-%d %H:%M:%S') AS lastDetection
    FROM source
    GROUP BY 1, 2
  )
  SELECT
    'Nicaragua' AS country, 'UTC' AS timezone,
    false AS harmonized, false AS coverageVerified,
    'FIRMS pipeline: processed hotspots.parquet' AS source,
    (SELECT count(*)::INTEGER FROM source) AS totalRecords,
    (SELECT strftime(min(acq_datetime), '%Y-%m-%d') FROM source) AS firstDetection,
    (SELECT strftime(max(acq_datetime), '%Y-%m-%d') FROM source) AS lastDetection,
    (SELECT list(monthly ORDER BY year, month) FROM monthly) AS months
) TO '../frontend/src/data/historical_monthly.json' (FORMAT JSON, ARRAY false);
