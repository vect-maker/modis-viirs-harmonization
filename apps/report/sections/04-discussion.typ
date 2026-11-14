#import "../template.typ": todo

= Discussion

== Scientific and Operational Significance

The Nicaragua 2000–2025 record highlights the core challenge of multi-sensor fire monitoring: raw counts jump from 2,419 (April 2011) to 49,025 (April 2020) largely because 375 m VIIRS instruments resolve smaller, lower-FRP fires (`~10.6 MW` mean FRP vs. `~32.9 MW` for MODIS) and provide multiple pixel detections per 1 km MODIS footprint.

Our point-grain-preserving harmonization design (@eq:weight) bridges this transition without discarding native coordinates, timestamps, or FRP attributes. Crucially, the frontend explicitly marks unharmonized archives (`harmonized: false`, `coverageVerified: false`) so emergency managers and scientists are never misled by uncalibrated sensor transitions.

== Architectural and Reproducibility Advantages

+ *Local-First Analytical ETL:* Combining SQLite (`ArchiveFile` state machine) with out-of-core DuckDB SQL (`max_memory = '10GB'`, ZSTD Parquet) enables multi-decade country archives to be fused and normalized on commodity hardware without a distributed cluster.
+ *Deterministic Deduplication:* RFC 4122 UUIDv5 primary keys ensure idempotent re-ingestion across overlapping NASA FIRMS updates.
+ *Reproducible Container Deployment:* The root `compose.yml` and `Caddyfile` orchestrate PostGIS 17-3.5, the Vue 3 + Nginx frontend, the FastAPI backend stack, and Caddy 2.9 automatic HTTPS on rootless Ubuntu hosts (`net.ipv4.ip_unprivileged_port_start=80`).

== Current Limitations and Future Work

+ *Meteorological & Training Scope:* `WeatherDataClient` currently relies on NASA POWER daily aggregates (`T2M`, `RH2M`, `WS10M`, `WD10M`, `PRECTOTCORR`) rather than sub-daily reanalysis, and `FirePredictor` trains `RandomForestRegressor` on-demand in memory rather than serving versioned pre-trained model artifacts. Additionally, centroid-based velocity represents apparent detection-cluster drift rather than physical flame-front spread rate.
+ *Empirical Calibration Scope:* The default `2.25` MODIS-to-VIIRS multiplicity fallback in `sql/test_spatial_harmonization.sql` requires cross-biome empirical calibration across diverse fire regimes beyond the Chilecito ROI.
+ *Observation Coverage Verification:* Cloud cover and orbital swath gaps are not yet modeled (`coverageVerified: false`), meaning zero-detection calendar cells cannot yet distinguish absence of fire from absence of clear-sky observation.
+ *Near-Real-Time (NRT) Ingestion:* Automated scheduled fetching of daily FIRMS NRT feeds into PostGIS is planned as future work.
