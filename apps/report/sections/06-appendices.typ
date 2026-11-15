#import "../template.typ": todo

#heading(outlined: false, numbering: none)[Acknowledgments]

This work is developed for the *2026 NASA Space Apps Challenge* ("Harmonization of MODIS and VIIRS Hot Spots"). We utilize NASA Earthdata FIRMS active fire archives, NASA GIBS imagery, Esri World Imagery, DuckDB, PostGIS, MapLibre GL JS, and the open-source Python and Vue ecosystems.

#heading(outlined: false, numbering: none)[References]

+ NASA FIRMS (2026). *Fire Information for Resource Management System*. `https://firms.modaps.eosdis.nasa.gov`
+ NASA Space Apps Challenge (2026). *Harmonization of MODIS and VIIRS Hot Spots*. `https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/`
+ Giglio, L., Schroeder, W., & Justice, C. O. (2016). "The collection 6 MODIS active fire detection algorithm and fire products." *Remote Sensing of Environment*, 178, 31–41.
+ Schroeder, W., et al. (2014). "The New VIIRS 375 m active fire detection data product: Algorithm description and initial assessment." *Remote Sensing of Environment*, 143, 85–96.

#v(0.6em)
#set heading(numbering: "A.1")
#counter(heading).update(0)

= Data Availability

- *NASA FIRMS Archives:* Country-level yearly MODIS (`2000`–`2025`), VIIRS Suomi-NPP (`2012`–`2025`), and VIIRS NOAA-20/JPSS-1 (`2018`–`2025`) CSV/Parquet archives accessed via `FIRMS_MAP_KEY`.
- *Nicaragua Demonstration Dataset:* 800,480 raw detections (`2000-11-01` to `2025-12-31`) exported to `apps/frontend/src/data/historical_monthly.json` and 5,000-point active-season sample (`2024-03-01` to `2024-05-31`) in `sample_hotspots.json`.
- *Source Repository:* `https://github.com/vect-maker/firms-harmonizer-etl`

= System Requirements & Deployment

- *Containerized Stack (`compose.yml`):* PostgreSQL 17 + PostGIS 3.5 (`postgis:17-3.5`), Node 24 build $->$ `nginx:alpine` frontend, Python 3.13-slim FastAPI backend, and `caddy:2.9-alpine` reverse proxy (`CADDY_DOMAIN`).
- *Rootless Ubuntu 24.04 Host:* Requires `net.ipv4.ip_unprivileged_port_start=80` for ports 80/443 and `just` (`--unstable` for `mod` syntax on `just` 1.21.x, or `just >= 1.29`).
- *ETL Execution:* DuckDB configured with `max_memory = '10GB'` and `threads = 8`.

= Software Dependencies

- *Pipeline (`apps/pipeline`, Python `>=3.12`):* `sqlmodel`, `httpx2[http2]`, `pandas[parquet,feather]`, `dotenv`, `duckdb` CLI (with `spatial`), `ruff`, `basedpyright`.
- *Backend Stack (`apps/backend`, Python `>=3.12`):* `fastapi[standard]`, `sqlmodel`, `httpx`, `psycopg[binary]>=3.3.9`, `numpy`, `scikit-learn`, `scipy`, `duckdb`, `pytest`, `ruff`, `basedpyright`.
- *Frontend (`apps/frontend`):* `vue@^3.5`, `pinia@^4.0`, `vue-router`, `maplibre-gl@^5.1`, `@mapbox/mapbox-gl-draw@^1.5`, `@turf/turf@^7.2`, `reka-ui@^2.0`, `@vueuse/core@^15.0`, `tailwindcss@^4.3`, `vite@^8.2`.

= Reproducibility Checklist

- `[x]` Source code and SQL transformations publicly available on GitHub.
- `[x]` Deterministic UUIDv5 key generation (`firms.nasa.gov` DNS namespace) and DuckDB/PostGIS cluster loading (`just pipeline db-load-clusters`).
- `[x]` Containerfiles (`prod.containerfile`, `debug.containerfile`) and `compose.yml` included.
- `[x]` Backend REST endpoints, NumPy/Scikit-learn analytics modules, and `pytest` / `basedpyright` verification suite implemented.
- `[ ]` #todo[Completed empirical spatial benchmark (`just pipeline benchmark-spatial`) and frontend live-API switchover.]

*Hackathon Project Information:* NASA Space Apps Challenge 2026 | Repository: `https://github.com/vect-maker/firms-harmonizer-etl` | Live Demo: #todo[Add deployed URL] | Team: #todo[Add team handles]
