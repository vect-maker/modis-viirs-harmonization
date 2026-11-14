#import "../template.typ": todo

= Conclusions

We have designed and implemented the core ETL pipeline, spatial data model, and interactive web visualization frontend for *FIRMS Harmonizer ETL*, targeting the 2026 NASA Space Apps Challenge on MODIS and VIIRS active fire harmonization.

== Key Achievements

- *Working Multi-Sensor ETL (`apps/pipeline`):* Quota-aware HTTP/2 ingestion from NASA FIRMS into partitioned Parquet, DuckDB Silver fusion across MODIS and VIIRS (`bright_mir`, `bright_tir`, unified confidence and satellite names), and deterministic UUIDv5 Gold Star Schema generation.
- *Point-Grain Harmonization Model:* A 5-class spatio-temporal quadrant co-detection taxonomy distinguishing simultaneous detections, VIIRS sensitivity gains, and Terra diurnal morning passes while preserving 100% of point-level metadata.
- *Interactive Web Dashboard (`apps/frontend`):* Vue 3.5 + MapLibre GL JS 5.1 interface with Turf.js polygon ROI filtering, a 2000–2025 logarithmic burning activity calendar (demonstrated on 800,480 Nicaragua detections), and RFC-4180 CSV export.
- *Containerized Stack:* Rootless Podman/Docker Compose setup with PostGIS 17-3.5, Nginx, FastAPI/SQLModel backend stack, and Caddy 2.9 TLS termination.

== Immediate Next Steps

+ Complete the FastAPI + Psycopg 3 backend endpoints (`apps/backend`) to serve live PostGIS spatial/calendar queries;
+ Run `just pipeline benchmark-spatial` and cross-biome calibration to replace placeholder metrics in Section 3;
+ Integrate cloud/swath coverage metadata to upgrade `coverageVerified` in the burning activity calendar.
