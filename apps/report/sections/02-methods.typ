#import "../template.typ": todo

= Methods

== Data Ingestion and Metadata Orchestration

We access NASA FIRMS country-level yearly archive files (`modis`, `viirs-snpp`, `viirs-jpss1`) via the FIRMS API (`https://firms.modaps.eosdis.nasa.gov/api`). Pipeline state is tracked in a local SQLite database (`data/pipeline.db`) using the `ArchiveFile` SQLModel table, which records remote file attributes (`filename`, `instrument`, `year`, `country`, `remote_subpath`, `remote_size`), download state (`status`, `download_attempts`, `local_path`), and ingestion status.

*Ingestion Features:*
+ *Quota-Aware Async Fetching:* `pipeline/fetcher.py` queries `/mapserver/mapkey_status/` before downloading and streams CSV payloads over HTTP/2 via `httpx2.AsyncClient`.
+ *Strict Type Parsing & Atomic Storage:* Raw CSVs are parsed with explicit `CSV_DTYPES` (`acq_time`, `version`, `confidence`, `satellite`, `instrument`, `daynight` as strings; `type` as `Int64`) and written atomically as Parquet files partitioned by `data/raw/{instrument}/{year}/{country}.parquet`.

== Silver-Layer Sensor Fusion

`sql/fuse_datasets.sql` executes in DuckDB (configured with `max_memory = '10GB'`, `threads = 8`, `preserve_insertion_order = false`) to consolidate all `completed` archive files into a unified Silver dataset (`data/processed/hotspots.parquet`, ZSTD-compressed).

#text(size: 8.5pt)[
  #table(
    columns: (30%, 35%, 35%),
    align: (left, left, left),
    table.header([Column], [MODIS Mapping], [VIIRS Mapping]),
    [`bright_mir`], [`brightness`], [`bright_ti4`],
    [`bright_tir`], [`bright_t31`], [`bright_ti5`],
    [`acq_datetime`], [`strptime(acq_date || ' ' || acq_time, '%Y-%m-%d %H%M')`], [Same],
    [`satellite`], [`Terra` / `Aqua`], [`N` $->$ `Suomi-NPP`, `N20` $->$ `NOAA-20`, `N21` $->$ `NOAA-21`],
    [`confidence`], [`try_cast(confidence AS INT)`], [`l` $->$ `20`, `n` $->$ `50`, `h` $->$ `90`],
    [`confidence_class`], [`<30` $->$ `l`, `<80` $->$ `n`, `>=80` $->$ `h`], [`lower(confidence)`],
  )
]
#v(0.3em)

== Gold-Layer Star Schema and Deterministic Identity

To prevent duplicate hotspot ingestion across overlapping archive updates and support relational/GIS queries in PostGIS, `sql/normalize_star_schema.sql` and `sql/schema.sql` normalize the Silver dataset into a Star Schema using RFC 4122 UUIDv5 keys seeded with the DNS namespace for `firms.nasa.gov` (`98b00dc4-63e7-5855-bfed-2cdc66170e68`):

- *`dim_country`:* `firms_uuid5('country:' || lower(trim(country)))`.
- *`dim_platform`:* `firms_uuid5('platform:' || lower(trim(satellite)) || ':' || lower(trim(instrument)))`.
- *`fact_hotspots`:* Keyed on `'detection:' || round(latitude, 5) || ':' || round(longitude, 5) || ':' || strftime(acq_datetime, '%Y-%m-%dT%H:%M:%S') || ':' || lower(trim(satellite)) || ':' || lower(trim(instrument))`.

In PostGIS (`sql/schema.sql`), `fact_hotspots` stores `geom GEOMETRY(Point, 4326)` indexed with a GIST spatial index (`idx_fact_hotspots_geom`), B-tree indexes on `acq_datetime`, `(country_id, acq_datetime)`, and `platform_id`, plus a backward-compatible `hotspots` view joining all three tables. Alongside the Star Schema, `sql/schema.sql` defines relational tables for cluster-level fire tracking and meteorological linkage: `firecluster` (using the `clusterstatus` enum), `clusterhotspots`, and `environmentalrecord`.

For full-archive spatial grouping prior to relational loading, `sql/cluster_hotspots.sql` executes a pure DuckDB SQL spatio-temporal grid clustering pass over `data/raw/**/*.parquet` using an approximate $1 "km"$ spatial cell ($0.009 degree$) and a $24 "h"$ temporal slot (`FLOOR(EPOCH(acq_datetime) / 86400.0)`), writing `fire_clusters.parquet` and `cluster_hotspots.parquet`. The `sql/load_clusters.sql` script and `justfile` (`db-load-clusters`, `db-load-nicaragua`) stream these Parquet outputs into PostGIS. Direction and speed expansion estimates (`dirExpansion`, `veloExpansion`) are decoupled from the ETL pipeline into a backend-only `FireClusterForecast` model (`apps/backend/model/FireClusterForecast.py`) and `FireForecastService.py` (invoked via `POST /fire-cluster-forecasts/calculate` using `fireClusterId` to query stored cluster hotspots).

== Multi-Stage Spatio-Temporal Harmonization Pipeline

To eliminate the sensor-transition discontinuity without discarding native point-grain coordinates, timestamps, or raw radiative energy measurements, `apps/pipeline/sql/harmonize/` executes a 4-stage out-of-core DuckDB SQL harmonization pipeline (`01_base_points.sql` through `04_harmonize_points.sql`), invoked via `just pipeline harmonize-data`:

+ *Stage 1: Base Point Enrichment & Local Solar Time (`01_base_points.sql`):*
  Because sun-synchronous orbital overpasses occur at constant local solar times ($"LST"$) rather than constant UTC, timestamps are transformed using the point longitude $lambda$:
  $ "LST" = ((( "hour"(t) + "minute"(t)/60.0 + lambda/15.0 ) mod 24.0) + 24.0) mod 24.0 $ <eq:solar-hour>
  Points are discretized into isotropic $~2.2 "km"$ quadrants using latitude-cosine meridian convergence correction ($"lat"_q = "round"(phi / 0.02) dot 0.02$, $"lon"_q = "round"((lambda dot cos("radians"(phi))) / 0.02) dot 0.02$) and 1-hour temporal bins ($"hour\_window" = "date\_trunc"("hour", t)$). Hours are partitioned into five orbital overpass regimes:
  - `MORNING_TERRA`: $8.5 <= "LST" < 12.0$ (Terra morning pass $~10:30$ LST);
  - `AFTERNOON_AQUA_VIIRS`: $12.0 <= "LST" < 16.0$ (Aqua $~13:30$ and VIIRS $~13:20–13:30$ LST);
  - `NIGHT_TERRA`: $20.0 <= "LST" < 23.5$ (Terra descending pass $~22:30$ LST);
  - `NIGHT_DAWN_AQUA_VIIRS`: $23.5 <= "LST" <= 24.0$ or $0.0 <= "LST" < 4.0$ (Aqua / VIIRS night passes);
  - `OFF_CYCLE`: other off-cycle or drifting overpasses.

+ *Stage 2: Quadrant-Hourly Co-Occurrence Aggregation (`02_quadrant_hourly.sql`):*
  Detections are aggregated by `(country, lat_q, lon_q, hour_window)` to tabulate `modis_in_cluster`, `viirs_in_cluster`, `modis_frp_sum`, and `viirs_frp_sum`.

+ *Stage 3: Empirical Per-Country Calibration (`03_country_calibration.sql`):*
  Across the concurrent overlap era ($"year" >= 2012$), national calibration factors are derived from simultaneous co-detections (Class A: `modis_in_cluster > 0` and `viirs_in_cluster > 0`) and regime totals:
  $ "raw\_pixel\_ratio" = (sum "viirs\_in\_cluster") / (sum "modis\_in\_cluster"), quad "raw\_frp\_ratio" = (sum "viirs\_frp\_sum") / (sum "modis\_frp\_sum") $ <eq:calibration-ratios>
  To ensure statistical significance, countries with $>= 100$ Class A clusters receive clamped empirical factors:
  - $f_"morning" = "round"("clamp"("raw\_pixel\_ratio", 1.0, 10.0), 2)$ (fallback: $2.20$);
  - $f_"afternoon" = "round"("clamp"("raw\_afternoon\_ratio", 1.0, 20.0), 2)$ (fallback: $6.12$);
  - $f_"night" = "round"("clamp"("raw\_night\_ratio", 1.0, 15.0), 2)$ (fallback: $4.50$);
  - $f_"frp" = "round"("clamp"("raw\_frp\_ratio", 0.5, 5.0), 2)$ (fallback: $1.14$).

+ *Stage 4: Point-Level Taxonomy, Weighting, and Calibrated FRP (`04_harmonize_points.sql`):*
  Every original detection is classified into one of six physical regimes and receives a VIIRS-equivalent weight $w_i$ and calibrated $"FRP"_"harm"$:
  $ w_i = cases(
    1.00 & "if" "VIIRS" quad ("VIIRS\_PRESERVED"),
    0.00 & "if MODIS and" "viirs\_in\_cluster" > 0 quad ("MODIS\_REDUNDANT\_CODETECTION"),
    f_"morning" & "if MODIS and" "overpass\_window" = "MORNING\_TERRA" quad ("MODIS\_UNIQUE\_MORNING"),
    f_"afternoon" & "if MODIS and" "overpass\_window" = "AFTERNOON\_AQUA\_VIIRS" quad ("MODIS\_SOLO\_AFTERNOON"),
    cases(
      f_"morning" & "if morning",
      f_"afternoon" & "if afternoon",
      f_"night" & "otherwise"
    ) & "if MODIS and" "year" < 2012 quad ("MODIS\_HISTORICAL\_PRE\_2012"),
    f_"night" & "otherwise" quad ("MODIS\_SOLO\_OTHER")
  ) $ <eq:weight>

  Calibrated FRP is assigned as:
  $ "FRP"_"harm" = cases(
    "FRP"_"native" & "if" "VIIRS",
    0.00 & "if MODIS and" "viirs\_in\_cluster" > 0,
    "round"("FRP"_"native" dot f_"frp", 2) & "otherwise"
  ) $ <eq:frp-harm>

  This design prevents duplicate fire counts during the 2012–2025 overlap era, captures Terra's exclusive morning diurnal signal, and scales pre-2012 MODIS counts and radiative power to VIIRS 375 m equivalence. Outputs are saved to `data/processed/hotspots_harmonized.parquet` and normalized into `fact_hotspots` in PostGIS.

== Interactive Burning Activity Calendar Frontend

The web application (`apps/frontend`) separates presentational components (`components/common/`, `components/ui/`) from Pinia-connected container components (`components/features/`, `components/map/`):

- *Spatial Map & ROI Selection:* `FireMap.vue` initializes MapLibre GL JS with a custom WebGL worker, NASA GIBS (MODIS Terra / VIIRS SNPP True Color) and Esri World Imagery basemaps, and `@mapbox/mapbox-gl-draw` + `@turf/turf` to compute exact ROI area ($"km"^2$) and filter hotspots in real time.
- *Burning Activity Calendar:* `HistoricalCalendar.vue` and `BurningCalendar.vue` render a year-by-month matrix (`2000`–`2025`) with sensor toggling (`All` / `MODIS` / `VIIRS`). Cell colors use a 5-step colorblind-safe logarithmic Thermal Inferno scale (`#2D1E3E` to `#FFE066`, with `#1F2730` for zero detections and transparent for missing/unverified coverage):
$ "level" = min(4, floor((ln(1 + c) / ln(1 + max(1, c_max))) dot 5)) $ <eq:logscale>
- *Daily Timeline & CSV Export:* `hotspotActivity.ts` aggregates detections per UTC day over the selected range, and `hotspotCsv.ts` exports filtered subsets as RFC-4180 CSV (`acq_datetime_utc`, `latitude`, `longitude`, `instrument`, `satellite`, `confidence_class`, `confidence`, `frp`, `bright_mir`, `daynight`).

== Backend Wildfire Spread Analytics and Predictive Modeling (`apps/backend`)

To serve live PostGIS queries and analyze fire propagation without loading large Pandas DataFrames into memory, `apps/backend` exposes paginated REST endpoints (`limit`, `offset`) across all core tables and views (`/hotspots/`, `/weather/`, `/clusters/`, `/clusters/{cluster_id}`, `/cluster-hotspots/`, `/environmental-records/`, `/countries/`, `/platforms/`, `/fact-hotspots/`, `/fire-cluster-forecasts/`), paired with a NumPy- and Scikit-learn-based analytics pipeline (`apps/backend/analytics/`) accessible via `/analysis/cluster-movement`, `/analysis/weather-correlation`, and `/analysis/predict`:

+ *Array-Based Preprocessing (`HotspotProcessor.py`):* Validates coordinates, timestamps, and FRP values from batched `HotspotRepository.iter_hotspots_filtered(...)` streams into `PreparedHotspots` (`float64` arrays and precomputed `coords_rad` in radians).
+ *Spatio-Temporal Clustering (`FireClusterer.py`):* Applies Scikit-learn `DBSCAN(metric="haversine", algorithm="ball_tree")` and `BallTree` spatial indexing over radian coordinates, paired with a dynamic temporal window (`time_window_hours = 24.0`, extending in `window_extension_hours = 12.0` increments up to `max_time_window_hours = 72.0` for confirmed fires reaching `min_samples`) while flagging isolated detections as noise (`-1`).
+ *Movement & Bearing Analysis (`FireMovementAnalyzer.py`):* Groups detections into configurable `interval_hours` bins, computes interval centroids, tracks gaps (`empty_intervals_before`), and calculates Haversine displacement, forward geographic bearing ($theta = "atan2"(y, x)$ mapped to $[0 degree, 360 degree)$ and 8 cardinal sectors), apparent centroid velocity ($"km/h"$, explicitly distinguished from physical flame-front speed), accumulated FRP, and direction-change flags (`direction_changed`).
+ *Meteorological Vector Integration (`WeatherDataClient.py`, `RequestWeather.py`, `WeatherAnalyzer.py`):* Queries NASA POWER daily parameters (`T2M`, `RH2M`, `WS10M`, `WD10M`, `PRECTOTCORR`), sanitizes `-999` sentinel values to `None` without fabricating missing records, converts meteorological "from" wind directions via $("wd" + 180 degree) mod 360 degree$ into displacement vector components ($u = V sin(theta)$, $v = V cos(theta)$), and evaluates wind–fire cosine alignment.
+ *Displacement Prediction (`FirePredictor.py`):* Trains a multi-output `RandomForestRegressor` predicting future eastward (`east_km`) and northward (`north_km`) centroid displacements from 10 historical predictors (latitude, longitude, FRP, hotspot count, wind speed, $u$, $v$, relative humidity, temperature, and prior displacement velocity). Models enforce a minimum sample threshold (`min_training_samples = 20`), use chronological fire-grouped splits to prevent future data leakage, reconstruct predicted bearing and distance, and report MAE, RMSE, $R^2$, mean angular error (degrees), and `feature_importances_`.
+ *SQL-First Dashboard & Chart Endpoints (`DashboardRepository.py`, `DashboardAnalytics.py`, `api/dashboard.py`):* Replaces heavy `pandas`/`geopandas`/`statsmodels` exploratory scripts with SQLModel/SQLAlchemy pushdown aggregations and NumPy/Scikit-learn analytics across 7 `/dashboard/*` endpoints:
  - `/dashboard/confidence-dbscan`: Maps `confidence` (`l -> 15`, `n -> 50`, `h -> high_value`) and aggregates unique value counts in SQL before running `DBSCAN`.
  - `/dashboard/correlations`: Computes Pearson $r$, $R^2$, $n$, mean, and standard deviation directly in SQL across `frp`, `confidence`, `bright_tir`, and `bright_mir`.
  - `/dashboard/annual-stats`: Computes per-year `count`, `sum`, `mean`, `std`, `min`, `p25`, `median`, `p75`, `p90`, `iqr`, and `max` (using `PERCENTILE_CONT` in PostgreSQL).
  - `/dashboard/spatial-density`: Bins detections into `cell_size_deg` spatial grid cells in SQL (`count`, `sum_frp`, `avg_frp`, `max_frp`) plus cell-count descriptive statistics.
  - `/dashboard/monthly-comparison`: Compares a target year against the historic monthly baseline (`mean`, `median`, `std`, `p25`, `p75`, `anomaly_abs`, `anomaly_pct`, `z_score`).
  - `/dashboard/spatial-anomalies`: Runs `IsolationForest` over `(latitude, longitude)` NumPy arrays returning anomaly counts, score statistics, and prioritized outlier points.
  - `/dashboard/monthly-forecast`: Trains a seasonal autoregressive `Ridge` model (lags 1, 2, 12, seasonal harmonics, and trend) on SQL-aggregated monthly series with 80%/95% prediction intervals and `MAE`, `MSE`, `RMSE`, `MAPE`, `SMAPE`, `R^2`, and `MBE`.
+ *Fire Calendar Aggregation (`FireCalendarRepository.py`, `FireCalendarService.py`, `api/fire_calendar.py`):* Exposes `GET /fire-calendar` with strict Pydantic validation (`FireCalendarQuery`: `year`, `month`, `start_date`, `end_date`, `country`, `min_confidence`, `confidence_class`, `satellite`, `instrument`, `daynight`, `min_frp`, `max_frp`, `cluster_id`, `aggregation` in `{day, week, month}`). Applies filters prior to PostgreSQL `DATE_TRUNC` grouping, tracks `new_fires` and `active_fires` from `FireCluster` lifespans (`datetimeStart`, `datetimeEnd`), and zero-fills intervals without detections.

#figure(
  table(
    columns: 4,
    table.header([*Module*], [*Statistical / ML Model*], [*Inputs & Features*], [*Outputs & Evaluation Metrics*]),
    [`FireClusterer`], [DBSCAN (`haversine`, `ball_tree`) + dynamic window ($24–72 "h"$)], [Radians `(lat, lon)`, `acq_datetime`], [Cluster labels, noise (`-1`)],
    [`DashboardRepository` / `dbscan`], [SQL `GROUP BY` + 1D `DBSCAN`], [Unique mapped `confidence` (`l/n/h`, int)], [Anomaly counts & percentages],
    [`DashboardRepository` / `corr`], [SQL Pearson $r$ & $R^2$], [`frp`, `confidence`, `bright_tir`, `bright_mir`], [$r$, $R^2$, $n$, mean, std],
    [`DashboardRepository` / `annual`], [SQL `PERCENTILE_CONT` & moments], [`frp`, `confidence`, `bright_tir`, `bright_mir`], [Count, sum, mean, std, `P25/P50/P75/P90`, `IQR`],
    [`DashboardAnalytics` / `iforest`], [`IsolationForest` (`n_estimators = 300`)], [`(latitude, longitude)`], [Outlier flags (`-1`/`1`), `decision_function` stats],
    [`DashboardAnalytics` / `forecast`], [Seasonal AR `Ridge` (lags 1, 2, 12 + harmonics)], [SQL monthly hotspot counts], [80%/95% PI, `MAE`, `MSE`, `RMSE`, `MAPE`, `SMAPE`, $R^2$, `MBE`],
    [`FirePredictor`], [Multi-output `RandomForestRegressor`], [10 historical & NASA POWER wind/weather features], [`east_km`, `north_km`, `MAE`, `RMSE`, $R^2$, angular error],
    [`FireCalendarService`], [SQL `DATE_TRUNC` + cluster overlap], [`hotspots`, `firecluster`], [`hotspot_count`, `new_fires`, `active_fires`, FRP & day/night],
  ),
  caption: [Summary of statistical and machine-learning models implemented in `apps/backend`.],
) <tab:backend-models>
