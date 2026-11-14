#import "../template.typ": todo

= Results

== Nicaragua Historical Archive Summary (2000–2025)

Using `sql/export_nicaragua_calendar.sql`, we aggregated the Silver-layer dataset (`data/processed/hotspots.parquet`) for Nicaragua into `apps/frontend/src/data/historical_monthly.json`. The archive spans `2000-11-01` through `2025-12-31` and contains *800,480* raw active fire detections across MODIS (2000–2025), VIIRS Suomi-NPP (2012–2025), and VIIRS NOAA-20/JPSS-1 (2018–2025).

Table 1 illustrates peak dry-season (April) detection counts across key sensor-transition eras, demonstrating why raw hotspot counts cannot be compared directly without harmonization:

#table(
  columns: (auto, auto, auto, auto, auto),
  align: (left, right, right, right, right),
  table.header([Period], [MODIS], [VIIRS], [Total], [Avg FRP (MW)]),
  [Apr 2005 (MODIS only)], [5,074], [--], [5,074], [31.09],
  [Apr 2011 (MODIS only)], [2,419], [--], [2,419], [32.92],
  [Apr 2012 (+ VIIRS SNPP)], [1,169], [7,964], [9,133], [11.19],
  [Apr 2018 (+ JPSS-1)], [2,318], [31,587], [33,905], [10.32],
  [Apr 2020 (All active)], [3,660], [45,365], [49,025], [10.64],
)
#v(0.3em)

As shown in Table 1, introducing VIIRS SNPP (2012) and NOAA-20 (2018) increases April hotspot counts by an order of magnitude while reducing mean FRP from \~31–33 MW (MODIS) to \~10–11 MW due to VIIRS's 375 m spatial resolution and higher sensitivity to smaller fires.

== Spatial Harmonization Prototype Benchmark

`sql/test_spatial_harmonization.sql` evaluates the 5-class spatio-temporal co-detection model on a regional bounding polygon in Chilecito / La Rioja, Argentina (`POLYGON((-68.2 -29.8, -66.8 -29.8, -66.8 -28.5, -68.2 -28.5, -68.2 -29.8))`).

#todo[Execute `just pipeline benchmark-spatial` and populate Table 2 with observed quadrant-hour counts, MODIS/VIIRS point totals, co-detection pixel ratios ($N_"VIIRS" / N_"MODIS"$), and mean FRP per anomaly class A–E.]

#table(
  columns: (auto, auto, auto, auto),
  align: (left, right, right, right),
  table.header([Anomaly Class], [Quadrant-Hours], [MODIS Pts], [VIIRS Pts]),
  [A: Simultaneous Co-Detection], [#todo[N]], [#todo[N]], [#todo[N]],
  [B: VIIRS Afternoon Solo], [#todo[N]], [0], [#todo[N]],
  [C: Terra Morning Solo], [#todo[N]], [#todo[N]], [0],
  [D: VIIRS Night/Off-Cycle], [#todo[N]], [0], [#todo[N]],
  [E: MODIS Other Solo], [#todo[N]], [#todo[N]], [0],
)
#v(0.3em)

== Pipeline, PostGIS Ingestion, and Backend Verification

Pure DuckDB SQL spatio-temporal grid clustering (`sql/cluster_hotspots.sql`, $0.009 degree$ cell, $24 "h"$ slot) across the full `data/raw/**/*.parquet` archive (`2000-11-01 02:31:00` to `2025-12-31 19:30:00`) produced `fire_clusters.parquet` (`16.5 MB`, `570,387` clusters) and `cluster_hotspots.parquet` (`25.0 MB`, `809,149` hotspots; global average FRP `12.0 MW`, maximum FRP `3,041.7 MW`). PostGIS loading via `sql/load_clusters.sql` (`just pipeline db-load-clusters` and `db-load-nicaragua`) ingested `570,387` `firecluster` rows in `3.515 s`, `809,149` `clusterhotspots` rows in `9.881 s`, and `809,149` `fact_hotspots` rows (`6` `dim_country`, `4` `dim_platform`) in `32.795 s`.

In `apps/backend`, static type checking with `basedpyright` passes with `0 errors, 0 warnings, 0 notes` across the analytics, repository, and API modules (including `api/fire_cluster_forecast.py`, `DashboardRepository.py`, `DashboardAnalytics.py`, and `api/dashboard.py`), and the full backend `pytest` unit/API suite passes (`22 passed in 5.72s` across `test_clustering.py`, `test_movement.py`, `test_weather.py`, `test_predictor.py`, `test_api_analysis.py`, and `test_dashboard.py`).

#todo[Record DuckDB execution times for `just pipeline fuse-data` and `just pipeline normalize-data`, as well as frontend MapLibre GL JS rendering frame rates on 5,000+ points.]
