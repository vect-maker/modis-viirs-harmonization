#import "../template.typ": todo

= Methods

== Data Ingestion and Metadata Orchestration

We access NASA FIRMS country-level yearly archive files (`modis`, `viirs-snpp`, `viirs-jpss1`) via the FIRMS API (`https://firms.modaps.eosdis.nasa.gov/api`). Pipeline state is tracked in a local SQLite database (`data/pipeline.db`) using the `ArchiveFile` SQLModel table, which records remote file attributes (`filename`, `instrument`, `year`, `country`, `remote_subpath`, `remote_size`), download state (`status`, `download_attempts`, `local_path`), and ingestion status.

*Ingestion Features:*
+ *Quota-Aware Async Fetching:* `pipeline/fetcher.py` queries `/mapserver/mapkey_status/` before downloading and streams CSV payloads over HTTP/2 via `httpx2.AsyncClient`.
+ *Strict Type Parsing & Atomic Storage:* Raw CSVs are parsed with explicit `CSV_DTYPES` (`acq_time`, `version`, `confidence`, `satellite`, `instrument`, `daynight` as strings; `type` as `Int64`) and written atomically as Parquet files partitioned by `data/raw/{instrument}/{year}/{country}.parquet`.

== Silver-Layer Sensor Fusion

`sql/fuse_datasets.sql` executes in DuckDB (configured with `max_memory = '10GB'`, `threads = 8`, `preserve_insertion_order = false`) to consolidate all `completed` archive files into a unified Silver dataset (`data/processed/hotspots.parquet`, ZSTD-compressed).

#table(
  columns: (auto, auto, auto),
  align: (left, left, left),
  table.header([Unified Column], [MODIS Mapping], [VIIRS Mapping]),
  [`bright_mir`], [`brightness`], [`bright_ti4`],
  [`bright_tir`], [`bright_t31`], [`bright_ti5`],
  [`acq_datetime`], [`strptime(acq_date || ' ' || acq_time, '%Y-%m-%d %H%M')`], [Same],
  [`satellite`], [`Terra` / `Aqua`], [`N` $->$ `Suomi-NPP`, `N20` $->$ `NOAA-20`, `N21` $->$ `NOAA-21`],
  [`confidence`], [`try_cast(confidence AS INTEGER)`], [`l` $->$ `20`, `n` $->$ `50`, `h` $->$ `90`],
  [`confidence_class`], [`<30` $->$ `l`, `<80` $->$ `n`, `>=80` $->$ `h`], [`lower(confidence)`],
)
#v(0.3em)

== Gold-Layer Star Schema and Deterministic Identity

To prevent duplicate hotspot ingestion across overlapping archive updates and support relational/GIS queries in PostGIS, `sql/normalize_star_schema.sql` and `sql/schema.sql` normalize the Silver dataset into a Star Schema using RFC 4122 UUIDv5 keys seeded with the DNS namespace for `firms.nasa.gov` (`98b00dc4-63e7-5855-bfed-2cdc66170e68`):

- *`dim_country`:* `firms_uuid5('country:' || lower(trim(country)))`.
- *`dim_platform`:* `firms_uuid5('platform:' || lower(trim(satellite)) || ':' || lower(trim(instrument)))`.
- *`fact_hotspots`:* Keyed on `'detection:' || round(latitude, 5) || ':' || round(longitude, 5) || ':' || strftime(acq_datetime, '%Y-%m-%dT%H:%M:%S') || ':' || lower(trim(satellite)) || ':' || lower(trim(instrument))`.

In PostGIS (`sql/schema.sql`), `fact_hotspots` stores `geom GEOMETRY(Point, 4326)` indexed with a GIST spatial index (`idx_fact_hotspots_geom`), B-tree indexes on `acq_datetime`, `(country_id, acq_datetime)`, and `platform_id`, plus a backward-compatible `hotspots` view joining all three tables.

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
