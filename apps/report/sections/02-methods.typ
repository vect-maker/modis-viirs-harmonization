= Implemented Method

== Data pipeline and technology stack

PyroTrace separates data acquisition, analytical transformation, spatial storage, and task orchestration into distinct layers so that multi-year satellite archives can be processed reliably on a single workstation without exhausting memory.

Raw active-fire archives are retrieved from the NASA FIRMS API as CSV files. Python scripts (`sync_meta.py`, `transform_meta.py`, `fetcher.py`, and `sync_local_files.py`) manage API transaction budgets, track which country-year-instrument files exist on disk in a local SQLite catalog (`data/pipeline.db`), and write downloaded records atomically as columnar Parquet files (`data/raw/<instrument>/<year>/<country>.parquet`). Python is used strictly for API communication, state tracking, and CSV-to-Parquet conversion rather than whole-archive analytical processing.

Processing multi-year continental or global archives on a single machine with in-memory tools such as pandas risks memory exhaustion. Instead, all dataset fusion (`fuse_datasets.sql`), four-stage harmonization (`sql/harmonize/`), star-schema normalization (`normalize_star_schema.sql`), and fire-event clustering (`sql/clusters/`) are written as pure DuckDB SQL queries. DuckDB executes vectorized, out-of-core operations directly over local Parquet files with bounded memory and disk spilling, and reads the SQLite catalog via `sqlite_scan`. Using DuckDB's `postgres` and `spatial` extensions, the same engine also bulk-loads the resulting Gold Parquet tables and clustered geometries directly into the production PostgreSQL database (`load_star_schema.sql`, `load_clusters.sql`).

Processed star-schema tables (`dim_country`, `dim_platform`, `fact_hotspots`) and fire-event footprints are stored in PostgreSQL with the PostGIS extension (`setup.sql`, `schema.sql`), providing indexed spatial geometries (`ST_Point` and polygon footprints) for the FastAPI backend and interactive map. Common project commands are codified in modular `justfile` recipe files (a root `justfile` delegating to `apps/pipeline/justfile`, `apps/report/justfile`, and sibling service modules), standardizing environment setup, API fetching, DuckDB SQL execution, PostGIS loading, and report compilation into single-command targets.

#figure(
  {
    set par(justify: false)
    table(
      columns: (27%, 24%, 49%),
      align: (left, left, left),
      table.header([Layer], [Tool], [Role and selection rationale]),
      [Ingestion & tracking], [Python, SQLite, Parquet], [Fetches NASA FIRMS API CSVs, tracks downloaded files on disk, and stores columnar raw archives.],
      [Transform & load], [DuckDB SQL], [Replaces in-memory pandas for single-machine out-of-core SQL transforms and direct PostgreSQL loading.],
      [Production store], [PostgreSQL + PostGIS], [Serves normalized star-schema records and spatial geometries to the application backend.],
      [Backend API], [FastAPI + SQLModel], [Provides rapid REST and SSE endpoint development with shared Pydantic and SQLAlchemy models.],
      [State & event bus], [NATS JetStream], [Persists worker KV cursors and SSE presence, and routes real-time events across API replicas.],
      [Task runner], [`justfile`], [Centralizes common pipeline, database, and report commands as versioned recipes.],
    )
  },
  caption: [Core ETL and orchestration stack used by the PyroTrace pipeline.],
)

== Transformation and loading phases

Once raw country-year-instrument Parquet files are registered on disk, the DuckDB pipeline processes them through four sequential stages, each exposed as a `justfile` recipe:

1. *Fuse dataset (`fuse_datasets.sql`, `just pipeline::fuse-data`):* Reads the SQLite file catalog (`sqlite_scan`) for completed raw Parquet files (scoped to Central America by default, or all countries globally) and unifies MODIS and VIIRS records into a single ZSTD-compressed Silver table (`data/processed/hotspots.parquet`). This stage parses timestamps, aligns MIR and TIR brightness column names, expands VIIRS satellite codes, and maps categorical VIIRS confidence (`l`, `n`, `h`) to numeric storage codes (`20`, `50`, `90`).
2. *Harmonize data (`sql/harmonize/01` to `04`, `just pipeline::harmonize-data`):* Executes four sequential SQL scripts over the Silver table to compute local solar hours and spatial-hourly keys (`01_base_points.sql`), detect candidate MODIS-VIIRS co-occurrences (`02_quadrant_hourly.sql`), derive country-level ratios and fallback factors (`03_country_calibration.sql`), and assign point-level categories, experimental weights, and derived FRP (`04_harmonize_points.sql`), outputting `data/processed/hotspots_harmonized.parquet`.
3. *Normalize data (`normalize_star_schema.sql`, `just pipeline::normalize-data`):* Converts the harmonized table into a Gold star schema under `data/processed/star/` (`dim_country.parquet`, `dim_platform.parquet`, and deduplicated `fact_hotspots.parquet`). Deterministic RFC 4122 UUIDv5 keys (`firms_uuid5`) are computed from natural attributes so repeated pipeline runs remain idempotent.
4. *Load data (`load_star_schema.sql`, `just pipeline::db-load`):* Uses DuckDB's `postgres` and `spatial` extensions to attach the production PostgreSQL/PostGIS database (`$DATABASE_URL`), truncate existing tables, and bulk-stream the Gold star-schema Parquet files while constructing `ST_Point` geometries. An accompanying clustering stage (`just pipeline::cluster-events`) groups hotspots into fire-event footprints and loads them into PostGIS for map rendering.

#figure(
  {
    set par(justify: false)
    table(
      columns: (28%, 72%),
      align: (left, left),
      table.header([Phase & recipe], [Primary output & purpose]),
      [1. Fuse\ (`fuse-data`)], [Produces unified Silver `hotspots.parquet` from raw MODIS and VIIRS Parquet files.],
      [2. Harmonize\ (`harmonize-data`)], [Produces `hotspots_harmonized.parquet` with weights, categories, and derived FRP.],
      [3. Normalize\ (`normalize-data`)], [Splits into Gold star-schema Parquet files (`dim_country`, `dim_platform`, `fact_hotspots`) with UUIDv5 keys.],
      [4. Load\ (`db-load`)], [Bulk-inserts Gold tables into PostgreSQL/PostGIS with `ST_Point` geometries.],
    )
  },
  caption: [Sequential DuckDB SQL transformation and loading phases.],
)

== Live API ingestion worker

Alongside the batch archive pipeline, a containerized Python worker (`apps/worker`) connects directly to the live NASA FIRMS Area CSV API to bridge historical archive gaps and maintain near-real-time (NRT) updates in PostgreSQL/PostGIS. Its lifecycle proceeds in two phases, supported by polygon-based country resolution.

In the first phase, a quota-aware catch-up process (`catchup.py`) resumes from a persisted NATS JetStream KV cursor (`catchup.cursor`), or from the latest stored `acq_datetime` in `fact_hotspots` when no cursor is present. It queries a regional bounding box (`FIRMS_AREA_BBOX`, defaulting to Central America) in 5-day batches across MODIS, Suomi-NPP, NOAA-20, and NOAA-21, selecting Standard Processing (`_SP`) or Near Real-Time (`_NRT`) feeds according to FIRMS data availability. Before each request, the worker checks the `MAP_KEY` transaction budget (`FIRMS_QUOTA_RESERVE = 50`). When the quota is approached or an HTTP 429 response occurs, it pauses for `CATCHUP_COOLDOWN_SECONDS` (default 610 s) and resumes from the saved cursor until caught up to the current UTC date.

Once catch-up completes, the worker transitions to near-real-time polling (`nrt_sync.py`), querying the four NRT feeds every `NRT_POLL_INTERVAL_SECONDS` (default 300 s) with a 2-day sliding window (`day_range = 2`) to capture newly available satellite overpasses. Because Area API responses return rectangular bounding-box detections without country labels, `country_resolver.py` tests each coordinate against `central_america.geojson` polygons using a Shapely `STRtree` spatial index and discards points outside the seven target countries. Valid detections receive the same deterministic `firms_uuid5` key in `hotspot_writer.py` and are inserted idempotently (`ON CONFLICT DO NOTHING`) into the PostGIS star schema.

== Backend service and NATS coordination

The application backend (`apps/backend`) is implemented with FastAPI and SQLModel. This stack was selected for rapid prototype development, automatic OpenAPI schema generation, and unified Pydantic validation and SQLAlchemy ORM mapping over the PostGIS star schema. Given additional engineering time, performance-critical API paths could be migrated from Python to a compiled systems framework such as Rust with Axum while keeping the same PostgreSQL/PostGIS schema and messaging contracts.

NATS serves as both a JetStream Key-Value (KV) store and a pub-sub event bus across the runtime services. As a KV store, the ingestion worker persists its operational state in the `worker_state` bucket (`catchup.cursor`, `catchup.completed`, `catchup.last_progress`, and `nrt.last_sync`), while FastAPI replicas record active Server-Sent Events (SSE) client streams in the `sse_presence` bucket (with a 45 s default TTL). As an event bus, `NatsService` publishes global notifications on `firms.sse.broadcast` and routes targeted user or tenant envelopes to specific backend replicas via `firms.sse.instance.<instance_id>`, falling back to local in-memory delivery when `NATS_URL` is unconfigured. Meanwhile, newly ingested hotspots written by the worker into PostgreSQL/PostGIS become immediately queryable by FastAPI repositories.

== Inputs and schema alignment

The source is a Silver Parquet table with country, native coordinates, UTC acquisition time, satellite, instrument, brightness temperatures, confidence, FRP, pixel scan/track dimensions, day/night flag, version, and anomaly type.

The fusion SQL renames MODIS brightness and VIIRS I4 to a shared MIR column, and MODIS band 31 and VIIRS I5 to a shared TIR column. Shared names do not make the spectral measurements identical. VIIRS confidence categories are mapped to numeric codes 20, 50, and 90 for storage; these codes are not calibrated detection probabilities or demonstrated equivalents of MODIS confidence. The weighting stages do not currently restrict anomaly type or confidence. A vegetation-fire study must define these filters explicitly @firmsmodis @firmsviirs.

== Local solar time and candidate cells

Let $h$ and $m$ be UTC acquisition hour and minute, and $lambda$ longitude in degrees, positive eastward. The code calculates:
$ h_s = h + m/60 + lambda/15 $ <eq:solar-hour>
$ "LST" = ((h_s " mod " 24) + 24) " mod " 24 $

Here 60 converts minutes to hours; 15 follows from 360 degrees per 24 hours. The result is a longitude-based local mean solar-hour approximation, not civil time or an exact apparent-solar-time solution. The code does not use a solar-time-shifted date for grouping.

#figure(
  table(
    columns: (48%, 52%),
    table.header([Window label], [Solar-hour interval]),
    [Morning], [08:30 to before 12:00],
    [Afternoon], [12:00 to before 16:00],
    [Terra-night label], [20:00 to before 23:30],
    [Dawn/night label], [23:30 to 24:00; 00:00 to before 04:00],
    [Off-cycle], [All remaining hours],
  ),
  caption: [Project-selected windows. Labels describe time bins; they do not identify the satellite or prove simultaneous observation.],
)

With latitude $phi$ and a project-selected angular step $d=0.02 degree$, spatial keys are:
$ y_q = d "round"(phi/d) $ <eq:grid-lat>
$ x_q = d "round"((lambda cos(phi))/d) $ <eq:grid-lon>

The SQL converts latitude to radians before evaluating cosine. A 0.02-degree latitude step is about 2.2 km. The longitude transformation is an approximate indexing rule; it is not a validated equal-distance or equal-area projection. Neighboring detections can fall on opposite cell boundaries. Pixel footprint dimensions are retained but not used in this matching rule.

Acquisition time is truncated to the UTC hour. The key is country, $y_q$, $x_q$, and truncated hour. Thus 18:59 and 19:01 are separated despite being only two minutes apart.

== Co-occurrence and country ratios

For each key $q$, define $M_q$ and $V_q$ as MODIS and VIIRS record counts. A candidate co-occurrence belongs to set $A$ when both counts are positive. This is a bin-level association, not a verified physical duplicate.

For records from 2012 onward, the implementation calculates:
$ r_c = (sum_(q in A) V_q)/(sum_(q in A) M_q) $ <eq:pixel-ratio>
$ r_p = (sum_(q in A) P_(V,q))/(sum_(q in A) P_(M,q)) $ <eq:frp-ratio>

$P_(V,q)$ and $P_(M,q)$ are sums of recorded FRP values, with missing values treated as zero by the current SQL. In addition:
$ r_a = N_(V,a)/N_(M,a), quad r_n = N_(V,n)/N_(M,n) $ <eq:regime-ratios>

The subscript $a$ denotes afternoon totals; $n$ combines both night windows and off-cycle observations. These totals do not require spatially matched observations. All VIIRS platforms are pooled.

The code uses $r_c$ for the morning factor even though $A$ is not restricted to morning observations. Transfer of that relationship to Terra morning observations is an untested assumption.

== Parameter selection

When at least 100 candidate co-occurrence groups exist for a country and the required ratio is defined, factors are computed with:
$ f = "round"(max(l,min(r,u)),2) $ <eq:clamp>

Here $l$ and $u$ are bounds; 2 is the number of decimal places. Undefined ratios or insufficient groups invoke the following fallbacks.

#figure(
  table(
    columns: (18%, 22%, 30%, 30%),
    align: (left, center, center, center),
    table.header([Factor], [Ratio], [Bounds], [Fallback]),
    [$f_m$], [$r_c$], [1 to 10], [2.20],
    [$f_a$], [$r_a$], [1 to 20], [6.12],
    [$f_n$], [$r_n$], [1 to 15], [4.50],
    [$f_p$], [$r_p$], [0.5 to 5], [1.14],
  ),
  caption: [Implemented project parameters. Published empirical derivations of these fallback values were not found.],
)

The threshold 100 is a minimum-sample heuristic; it is not a statistical significance test. No confidence intervals, effective sample sizes, or uncertainty propagation are currently produced. Clipping bounds and two-decimal rounding are engineering choices, not validation results. Unsupported regional or physical interpretations of the fallback values are not asserted.

== Point weights and the monthly index

Let $C_i=1$ when a MODIS record shares its candidate key with at least one VIIRS record, and $C_i=0$ otherwise. The actual weighting rule is:
$ w_i = cases(
  1 & i in V,
  0 & i in M " and " C_i=1,
  f_m & i in M " in morning",
  f_a & i in M " in afternoon",
  f_n & "remaining MODIS"
) $ <eq:weight>

The morning and afternoon branches apply after the co-occurrence branch. Six stored categories distinguish VIIRS-preserved, MODIS-suppressed, unique-morning MODIS, historical MODIS, afternoon-only MODIS, and other MODIS records. The historical label does not introduce a separate historical coefficient: the same time-window factors apply before 2012. The morning category takes precedence over the historical category in the SQL.

For month $t$, the experimental activity index is:
$ A_t = sum_(i in t) w_i $ <eq:activity>

This sum does not create additional point locations. Fractional units are weighted contributions, not independently counted fires, hectares, or a demonstrated reconstruction of missing VIIRS observations.

== Derived FRP and interpretation

With native FRP $P_i$, the derived field follows:
$ P_i^* = cases(
  P_i & i in V,
  0 & i in M " and " C_i=1,
  "round"(P_i f_p,2) & "other MODIS"
) $ <eq:frp-harm>

The actual SQL replaces missing native FRP with zero in this derived field, while retaining the native nullable field. Missing retrievals and measured zero power must remain distinguishable in downstream interpretation.

NASA's Collection 2 guide describes a hybrid retrieval using VIIRS I-band detections and M13 radiance; co-located 375 m detections share fractional FRP from the underlying retrieval @viirsguide2024. A smaller mean FRP per VIIRS record therefore does not by itself imply lower physical fire intensity.

A monthly sum of $P_i^*$ is an observation-summed power statistic. Energy requires time integration, for example $E=integral P(t) dif t$, together with assumptions about the intervals not observed. Neither energy nor burned area is estimated here.

== Fire event clustering for map representation

A single satellite hotspot represents one detected thermal pixel rather than an entire fire. Multiple MODIS and VIIRS detections from different overpasses often belong to the same burning episode. To avoid visual clutter and present a clearer operational picture on the map, the pipeline groups individual hotspots into *fire events* using two pure DuckDB SQL stages (`sql/clusters/01_assign_events.sql` and `02_build_clusters.sql`) before bulk-loading them into PostgreSQL/PostGIS:

- *Spatial cell rule:* Each hotspot is assigned to a `0.02`-degree grid cell (about 2.2 km). All detections sharing the same cell are candidates for the same event.
- *24-hour continuity rule:* Within each cell, detections are sorted by acquisition time. Consecutive detections remain in the same fire event as long as the gap between them is 24 hours or less. A gap longer than 24 hours starts a new event, which prevents continuous multi-day fires from being split artificially at midnight.
- *Footprint geometry rule:* For each fire event, DuckDB Spatial computes the center point (centroid) from its constituent hotspots and builds a perimeter polygon by taking the outer convex hull of the points and expanding it by a `0.0036`-degree buffer (about 400 m). This ensures that even a one- or two-hotspot event has a valid polygon and geodesic area in square kilometers.
- *Event summary and on-demand inspection:* Each event records the total hotspot count, separate MODIS and VIIRS counts, start and end timestamps, peak and total FRP, and the summed harmonization weight. On the web map, fire events are shown as ringed markers at regional zoom and dashed perimeter footprints when zoomed in; individual constituent hotspots are fetched only when the user clicks to inspect a specific event or switches to the raw hotspot layer.

As a known limitation of grid-based grouping, two nearby detections that fall on opposite sides of a `0.02`-degree cell boundary are assigned to separate events.

== Current application integration

The export SQL computes the experimental index and derived FRP alongside raw counts. Its processing flag is set by the export command, not by an independent validation gate.

The bundled JSON remains explicitly unharmonized, and the frontend calendar reads raw total or sensor-specific counts. The backend fire-calendar aggregation also uses raw counts and FRP. The weighted workflow is implemented in the pipeline but is not the metric currently displayed by this demonstration calendar.
