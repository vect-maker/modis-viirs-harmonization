#import "../template.typ": todo

= Introduction

== Background

Understanding how burning activity is distributed across Earth's surface over time—spanning wildfires in natural vegetation and forests as well as anthropogenic fires from agriculture, land-clearing, waste disposal, and industrial processes—enables emergency responders, scientists, and land managers to anticipate critical fire periods, guide monitoring efforts, and strengthen fire response. Satellite Earth Observation (EO) sensors operating in the mid-infrared (MIR) and thermal infrared (TIR) spectral ranges provide continuous, regional-to-global active fire hotspot detections, capturing fire location, Fire Radiative Power (FRP), and temporal evolution.

For more than two decades, NASA's Fire Information for Resource Management System (FIRMS) has distributed active fire detections from the Moderate Resolution Imaging Spectroradiometer (MODIS) aboard the Terra and Aqua satellites (2000–present). As MODIS approaches the end of its operational life, continuity is provided by the Visible Infrared Imaging Radiometer Suite (VIIRS) aboard Suomi-NPP (2012–present), NOAA-20 / JPSS-1 (2018–present), and NOAA-21.

*Active Fire Record Harmonization Challenges:*
Direct comparison between raw MODIS and VIIRS hotspot counts introduces severe sensor-induced discontinuities:
+ *Spatial Resolution Disparity:* MODIS nominal nadir pixel resolution is \~1 km, whereas VIIRS I-band active fire detections resolve at 375 m (yielding multiple VIIRS pixels for a single MODIS fire footprint).
+ *Sensor Sensitivity & Confidence Scales:* VIIRS detects smaller and cooler fires (lower FRP) than MODIS, and the two instruments report incompatible confidence encodings (MODIS integer $0$–$100$ vs. VIIRS categorical `l` / `n` / `h`).
+ *Orbital Overpass Schedules:* Terra provides a morning pass (\~10:30 AM local solar time) with no VIIRS counterpart, whereas Aqua and VIIRS share afternoon (\~1:30 PM) and nighttime overpasses.
+ *Lack of Unified Long-Term Calendars:* Without harmonization, multi-decade burning activity calendars exhibit artificial jumps after 2012 and 2018 that reflect sensor transitions rather than true ecological or climatic fire regimes.

== System Overview and Architecture

To address these challenges for the 2026 NASA Space Apps Challenge, we present *FIRMS Harmonizer ETL*, an open-source, containerized platform that combines a local-first analytical ETL pipeline with an interactive spatial web application:

- *ETL & Harmonization Pipeline (`apps/pipeline`):* Python 3.12+ orchestration with SQLModel/SQLite metadata tracking, async HTTP/2 ingestion via `httpx2`, and high-throughput DuckDB SQL transformations producing ZSTD-compressed Silver and Star-Schema Gold Parquet datasets.
- *Spatial Database (`db` service):* PostgreSQL 17 with PostGIS 3.5 (`postgis:17-3.5`) storing the normalized star schema (`dim_country`, `dim_platform`, `fact_hotspots`) with GIST spatial and composite temporal indexes.
- *Backend API (`apps/backend`, in active development):* FastAPI service built on Python 3.12+, SQLModel, `httpx`, and Psycopg 3 (`psycopg[binary]`), designed to serve spatial and temporal queries from PostGIS to the frontend.
- *Web Application (`apps/frontend`):* Vue 3.5 (`<script setup lang="ts">`) + Vite 8.2 + Pinia 4.0 dashboard featuring a WebGL-accelerated MapLibre GL JS 5.1 globe/map, interactive polygon/bounding-box ROI drawing (`@mapbox/mapbox-gl-draw`, `@turf/turf`), a 2000–2025 burning activity calendar, daily activity charts, and RFC-4180 CSV export.
- *Edge Reverse Proxy (`caddy` service):* Caddy 2.9 (`caddy:2.9-alpine`) routing `/api/*` to the backend and `*` to the frontend with automatic HTTPS via `CADDY_DOMAIN`.

== Research Objectives

This work aims to:
+ Build a reproducible, quota-aware ingestion pipeline for multi-decade NASA FIRMS MODIS and VIIRS country archives;
+ Fuse heterogeneous MODIS and VIIRS schemas into a unified Silver Parquet dataset and a deterministic UUIDv5 Star Schema Gold layer;
+ Formulate a point-grain-preserving spatio-temporal co-detection model to quantify VIIRS-to-MODIS multiplicity and classify diurnal/sensitivity anomalies;
+ Deliver an accessible, color-blind-aware burning activity calendar and interactive GIS web interface with CSV export;
+ Package the full stack for reproducible rootless container deployment via Podman/Docker Compose.
