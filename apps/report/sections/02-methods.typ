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

For full-archive spatial grouping prior to relational loading, `sql/cluster_hotspots.sql` executes a pure DuckDB SQL spatio-temporal grid clustering pass over `data/raw/**/*.parquet` using an approximate $1\text{ km}$ spatial cell ($0.009^\circ$) and a $24\text{ h}$ temporal slot (`FLOOR(EPOCH(acq_datetime) / 86400.0)`), writing `fire_clusters.parquet` and `cluster_hotspots.parquet`. The `sql/load_clusters.sql` script and `justfile` (`db-load-clusters`, `db-load-nicaragua`) stream these Parquet outputs into PostGIS. Direction and speed expansion estimates (`dirExpansion`, `veloExpansion`) are decoupled from the ETL pipeline into a backend-only `FireClusterForecast` model (`apps/backend/model/FireClusterForecast.py`) and `FireForecastService.py`.

== Spatio-Temporal Harmonization and Anomaly Classification

`sql/test_spatial_harmonization.sql` implements a point-grain-preserving spatial-temporal harmonization prototype using DuckDB's `spatial` extension:

+ *Spatio-Temporal Binning:* Detections are grouped into \~2 km spatial quadrants (`round(latitude, 2)`, `round(longitude, 2)`) and 1-hour temporal windows (`date_trunc('hour', acq_datetime)`).
+ *Overpass Classification:* Hours are categorized into *Morning Pass (Terra)* (12:00–15:00 UTC), *Afternoon Pass (Aqua + VIIRS)* (16:00–20:00 UTC), and *Night / Off-Cycle Pass*.
+ *Five-Class Anomaly Taxonomy:*
  - *Class A:* Simultaneous Co-Detection (MODIS $> 0$ and VIIRS $> 0$ in same hour & quadrant).
  - *Class B:* VIIRS Afternoon Faint/Solo Fire (MODIS missed during afternoon pass).
  - *Class C:* Terra Morning Solo Fire (diurnal cycle with no VIIRS morning pass).
  - *Class D:* VIIRS Night/Off-Cycle Fire.
  - *Class E:* MODIS Other Solo Fire.
+ *Point-Level Harmonized Weight:* Every original detection retains its exact coordinates, timestamp, and FRP, receiving a weight $w_i$:
$ w_i = cases(
  1.0 & "if instrument" = "VIIRS",
  N_"VIIRS" / N_"MODIS" & "if MODIS and Class A",
  2.25 & "otherwise (default footprint multiplicity)"
) $ <eq:weight>

== Interactive Burning Activity Calendar Frontend

The web application (`apps/frontend`) separates presentational components (`components/common/`, `components/ui/`) from Pinia-connected container components (`components/features/`, `components/map/`):

- *Spatial Map & ROI Selection:* `FireMap.vue` initializes MapLibre GL JS with a custom WebGL worker, NASA GIBS (MODIS Terra / VIIRS SNPP True Color) and Esri World Imagery basemaps, and `@mapbox/mapbox-gl-draw` + `@turf/turf` to compute exact ROI area ($"km"^2$) and filter hotspots in real time.
- *Burning Activity Calendar:* `HistoricalCalendar.vue` and `BurningCalendar.vue` render a year-by-month matrix (`2000`–`2025`) with sensor toggling (`All` / `MODIS` / `VIIRS`). Cell colors use a 5-step logarithmic scale (`#482425` to `#ffa66a`, with `#273038` for zero detections and transparent for missing/unverified coverage):
$ "level" = min(4, floor((ln(1 + c) / ln(1 + max(1, c_max))) dot 5)) $ <eq:logscale>
- *Daily Timeline & CSV Export:* `hotspotActivity.ts` aggregates detections per UTC day over the selected range, and `hotspotCsv.ts` exports filtered subsets as RFC-4180 CSV (`acq_datetime_utc`, `latitude`, `longitude`, `instrument`, `satellite`, `confidence_class`, `confidence`, `frp`, `bright_mir`, `daynight`).

== Backend Wildfire Spread Analytics and Predictive Modeling (`apps/backend`)

To serve live PostGIS queries and analyze fire propagation without loading large Pandas DataFrames into memory, `apps/backend` exposes paginated REST endpoints (`limit`, `offset`) across all core tables and views (`/hotspots/`, `/weather/`, `/clusters/`, `/clusters/{cluster_id}`, `/cluster-hotspots/`, `/environmental-records/`, `/countries/`, `/platforms/`, `/fact-hotspots/`, `/fire-cluster-forecasts/`), paired with a NumPy- and Scikit-learn-based analytics pipeline (`apps/backend/analytics/`) accessible via `/analysis/cluster-movement`, `/analysis/weather-correlation`, and `/analysis/predict`:

+ *Array-Based Preprocessing (`HotspotProcessor.py`):* Validates coordinates, timestamps, and FRP values from batched `HotspotRepository.iter_hotspots_filtered(...)` streams into `PreparedHotspots` (`float64` arrays and precomputed `coords_rad` in radians).
+ *Spatio-Temporal Clustering (`FireClusterer.py`):* Applies Scikit-learn `DBSCAN(metric="haversine", algorithm="ball_tree")` and `BallTree` spatial indexing over radian coordinates, paired with a dynamic temporal window (`time_window_hours = 24.0`, extending in `window_extension_hours = 12.0` increments up to `max_time_window_hours = 72.0` for confirmed fires reaching `min_samples`) while flagging isolated detections as noise (`-1`).
+ *Movement & Bearing Analysis (`FireMovementAnalyzer.py`):* Groups detections into configurable `interval_hours` bins, computes interval centroids, tracks gaps (`empty_intervals_before`), and calculates Haversine displacement, forward geographic bearing ($theta = \operatorname{atan2}(y, x)$ mapped to $[0^\circ, 360^\circ)$ and 8 cardinal sectors), apparent centroid velocity ($\text{km/h}$, explicitly distinguished from physical flame-front speed), accumulated FRP, and direction-change flags (`direction_changed`).
+ *Meteorological Vector Integration (`WeatherDataClient.py`, `RequestWeather.py`, `WeatherAnalyzer.py`):* Queries NASA POWER daily parameters (`T2M`, `RH2M`, `WS10M`, `WD10M`, `PRECTOTCORR`), sanitizes `-999` sentinel values to `None` without fabricating missing records, converts meteorological "from" wind directions via $(\text{wd} + 180^\circ) \bmod 360^\circ$ into displacement vector components ($u = V \sin(\theta)$, $v = V \cos(\theta)$), and evaluates wind–fire cosine alignment.
+ *Displacement Prediction (`FirePredictor.py`):* Trains a multi-output `RandomForestRegressor` predicting future eastward (`east_km`) and northward (`north_km`) centroid displacements from 10 historical predictors (latitude, longitude, FRP, hotspot count, wind speed, $u$, $v$, relative humidity, temperature, and prior displacement velocity). Models enforce a minimum sample threshold (`min_training_samples = 20`), use chronological fire-grouped splits to prevent future data leakage, reconstruct predicted bearing and distance, and report MAE, RMSE, $R^2$, mean angular error ($^\circ$), and `feature_importances_`.
