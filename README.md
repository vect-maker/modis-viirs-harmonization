# PyroTrace

**PyroTrace** is an open-source data platform that harmonizes NASA FIRMS active-fire observations from **MODIS** (Terra & Aqua, 1 km, 2000–present) and **VIIRS** (Suomi-NPP, NOAA-20, NOAA-21, 375 m, 2012–present) into a single comparable record for the seven countries of Central America (Belize, Costa Rica, El Salvador, Guatemala, Honduras, Nicaragua, and Panama).

Built by **Team sdlg** for the **NASA Space Apps Challenge 2026** (*MODIS and VIIRS Hot Spots* — Managua Local Event, Nicaragua, November 14–15, 2026).

- **Live Deployment**: [pyrotrace.northcentralus.cloudapp.azure.com](https://pyrotrace.northcentralus.cloudapp.azure.com/)
- **Source Code**: [github.com/vect-maker/modis-viirs-harmonization](https://github.com/vect-maker/modis-viirs-harmonization)
- **Team**: Jose Miranda, Inti Montalvan, Joshua Ordóñez, Fernando Gómez, Geovanny Miranda, and Herman Rodríguez

---

## Why Harmonization Matters

When raw MODIS and VIIRS active-fire detections are added together, every year after 2012 appears to have several times more fire activity—not because of landscape changes, but because VIIRS detects far more small fires at 375 m resolution.

In the Central American FIRMS archive (**3,621,309 detections** from November 1, 2000 to December 31, 2025: 700,335 MODIS and 2,920,974 VIIRS):
- **Raw detections** jump by a factor of **6.41×** between 2011 and 2013 (while MODIS alone changes by **1.09×**).
- **PyroTrace's harmonized index** (expressed in VIIRS-equivalent detections) reduces that transition jump to **1.57×**, bringing both sensor eras onto a comparable scale around a median of ~169,000 VIIRS-equivalent detections per year.

### Four-Stage DuckDB Harmonization Method

Every original FIRMS detection is preserved and traceable. Instead of deleting records or replacing them with a derived grid, four DuckDB SQL stages (`apps/pipeline/sql/harmonize/`) assign each detection a category, a weight, and a derived Fire Radiative Power (FRP):

1. **Local Solar Time & Search Keys**: Converts UTC timestamps to local mean solar hour, assigns overpass windows (Morning Terra, Afternoon Aqua/VIIRS, Night Terra, Night & Dawn Aqua/VIIRS, Off-cycle), and indexes detections into $0.02^\circ$ spatial cells and hourly slots.
2. **MODIS–VIIRS Co-Detections**: Searches the $3 \times 3 \times 3$ neighboring cell/hour neighborhood in the same country for MODIS–VIIRS pairs within **2,200 m** and **3,600 s**. Matched detections are flagged as co-detections.
3. **Country Calibration**: Normalizes VIIRS detections by the number of active VIIRS platforms ($p_{c,y}$) and estimates bounded country-level factors ($f_m, f_a, f_n, f_p$) from the 2012+ overlap period (falling back to regional defaults when a country has fewer than 100 co-detected MODIS records).
4. **Weights & Derived FRP**: Assigns $w_i = 1 / p_{c,y}$ to VIIRS detections, $0$ to co-detected MODIS detections (already counted by VIIRS), and $f_m / f_a / f_n$ to unmatched MODIS detections by overpass window.

---

## Architecture & Monorepo Layout

```
├── apps/
│   ├── pipeline/        # Python archive downloader (SQLite catalog + Parquet),
│   │                    # DuckDB SQL fusion, 4-stage harmonization, star schema,
│   │                    # fire-event clustering, and PostGIS loader
│   ├── worker/          # Near-real-time (NRT) worker polling NASA FIRMS Area API
│   │                    # (MODIS, Suomi-NPP, NOAA-20, NOAA-21), Natural Earth country
│   │                    # resolution, PostGIS writes, and NATS JetStream events
│   ├── backend/         # FastAPI + SQLModel API (~40 OpenAPI endpoints), Ed25519 JWT
│   │                    # auth, SSE live alerts/presence, NASA POWER weather context,
│   │                    # spatial density, anomaly detection, and forecasts
│   ├── frontend/        # Vue 3 + TypeScript SPA (MapLibre GL JS, Pinia, Vue Router,
│   │                    # Tailwind CSS v4, Reka UI, NASA GIBS & Esri World Imagery)
│   └── report/          # Typst APA 7th edition proposal reports (EN & ES), technical
│                        # harmonization documentation, and synthetic SQL verification
├── shared/              # Shared Python packages (shared_core, firms_shared)
├── docs/                # Challenge specs, participant guide & harmonization.md
├── compose.yml          # Production stack (PostGIS, NATS, Backend, Worker, Frontend, Caddy)
├── debug.compose.yml    # Development/debug compose override
├── Caddyfile            # Reverse proxy configuration
└── justfile             # Root task runner delegating to app modules
```

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package & environment manager)
- [just](https://github.com/casey/just) (Command runner)
- [Podman](https://podman.io/) / `podman compose` (Containers for PostGIS, NATS, Caddy, and app services)
- [DuckDB CLI](https://duckdb.org/) (For running pipeline SQL and synthetic verification)
- [Node.js & npm](https://nodejs.org/) (For `apps/frontend`)
- [Typst](https://typst.app/) (Optional, for compiling reports in `apps/report`)

---

## Quick Start (Full Stack)

### 1. Configure Environment & Signing Keys

```bash
cp .env.example .env
# Edit .env and set FIRMS_MAP_KEY (and optionally CADDY_DOMAIN, DATABASE_URL, etc.)

just bootstrap-keys   # Generates Ed25519 JWT keys in apps/backend/keys/
```

### 2. Start Services with Podman Compose

```bash
# Production mode (behind Caddy on ports 80/443)
just up-build

# Development/debug mode
just up-build-debug

# Check logs or stop services
just logs
just down
```

---

## Data Pipeline & Reproduction

To reproduce the Central America archive, harmonization, star schema, and fire-event clustering from scratch:

```bash
cp apps/pipeline/.env.example apps/pipeline/.env
just db-up                      # Start PostgreSQL + PostGIS container
just pipeline setup-env         # Create uv venv and install pipeline dependencies

just pipeline sync-meta
just pipeline fetch-central-america
just pipeline fuse-data
just pipeline harmonize-data
just pipeline normalize-data
just pipeline db-schema
just pipeline db-load
just pipeline cluster-events
```

To fetch a single country/year instead of the full Central American archive:

```bash
just pipeline fetch-data --country NIC --year 2024
```

---

## Local App Development

Run `just --list` (or `just <module> --list`) to see all available recipes.

### Backend (`apps/backend`)

```bash
just backend setup-env
just backend dev        # Starts FastAPI dev server
just backend lint
just backend typecheck
```

### Worker (`apps/worker`)

```bash
just worker setup-env
just worker dev         # Starts NRT polling & catchup worker
just worker test        # Runs pytest suite
just worker lint
just worker typecheck
```

### Frontend (`apps/frontend`)

```bash
just frontend install
just frontend dev       # Starts Vite dev server
just frontend build     # Production build + type-check
just frontend lint
```

### Technical Reports & Verification (`apps/report`)

The report suite includes a synthetic verification script (`apps/report/validation/verify_prototype.py`) that executes the four production harmonization SQL files against 810 synthetic detections in DuckDB to verify tuple preservation, hour/cell boundary matching, multi-VIIRS platform invariance, and `NULL` FRP preservation.

```bash
just report::validate         # Run synthetic SQL verification
just report::build            # Compile English proposal report (output/report.pdf)
just report::build-es         # Compile Spanish proposal report (output/report-es.pdf)
just report::documentation    # Compile APA 7 harmonization docs (output/PyroTrace_Harmonization.pdf)
```

---

## Known Limitations & Roadmap

As documented in Section 6.3 and Section 7 of the technical report:

- **Residual Transition Step (~37%)**: A consistency check of harmonized index per MODIS detection shows a mean ratio of 5.40 (2003–2011) vs. 7.41 (2012–2025), indicating that MODIS-only afternoon/night factors should be recalibrated using matched observations rather than window totals.
- **Early Years (2001–2002)**: Aqua MODIS began in July 2002, so 2001–2002 lack the afternoon overpass; normalizing MODIS by active MODIS platform count is planned.
- **Provisional NRT Data**: Detections ingested by the 2026 NRT worker are displayed in the map and calendar but marked as provisional and excluded from historical baselines until processed through the harmonization pipeline.
- **Observation Opportunities**: Cloud cover and satellite overpass gaps are not yet modeled; missing detections do not guarantee absence of fire.
- **Historical Calendar**: Currently displays raw detection counts while the statistics panel presents both raw counts and the harmonized index.

---

## License

This project is licensed under the [Apache License 2.0](LICENSE) (`Apache-2.0`), an Open Source Initiative (OSI)-approved open-source license.
