# PyroTrace Monorepo

Monorepo hosting **PyroTrace** — the NASA FIRMS active fire data pipeline, backend API, technical report, and visualization frontend.

## Monorepo Layout

```
├── apps/
│   └── pipeline/                  # FIRMS Data Pipeline & ETL
│       ├── data/                  # SQLite db, raw parquet, and processed artifacts
│       ├── pipeline/              # Python source (metadata, fetcher, DB models)
│       ├── sql/                   # DuckDB transformations & PostGIS schemas
│       ├── pyproject.toml         # Pipeline dependencies & tool configs
│       ├── requirements.txt
│       ├── uv.lock
│       └── justfile               # Pipeline tasks
├── docs/                          # Architecture & challenge specifications
├── compose.yml                    # Shared PostGIS container service
├── justfile                       # Root module delegator & container management
└── README.md
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Fast Python package manager)
- [just](https://github.com/casey/just) (Command runner)
- [DuckDB CLI](https://duckdb.org/)
- [Podman](https://podman.io/) or Docker (for PostGIS local container)

## Getting Started

### 1. Environment Setup
Copy the example environment files and configure credentials:
```bash
cp .env.example .env
cp apps/pipeline/.env.example apps/pipeline/.env
```

### 2. Provision Local Database
Start the PostgreSQL + PostGIS service from the repository root:
```bash
just db-up
```

### 3. Pipeline Application Setup
Set up the Python virtual environment for the pipeline:
```bash
just pipeline setup-env
```

### 4. Running Pipeline Tasks
Commands can be executed from the monorepo root via the `pipeline` module or inside `apps/pipeline`:

```bash
# From monorepo root
just pipeline sync-meta
just pipeline fetch-data --country NIC --year 2024
just pipeline fuse-data
just pipeline normalize-data
just pipeline lint
just pipeline typecheck

# Or directly within apps/pipeline
cd apps/pipeline
just sync-meta
just fuse-data
```

### 5. Frontend & Sample Data Workflow

In the current setup without an active backend API, the frontend loads sample active fire hotspots exported directly from the local DuckDB pipeline parquet files.

```bash
# 1. Export sample dataset (5000 hotspots from Nicaragua 2024 active season)
just sample-data

# 2. Run frontend development server
just frontend dev

# 3. Build & Typecheck
just frontend build
```

## Frontend Architecture

- **Framework**: Vue 3 (Composition API with `<script setup lang="ts">`)
- **Map & Spatial Engine**: MapLibre GL JS + `@mapbox/mapbox-gl-draw` + `@turf/turf`
- **Satellite Layers**: NASA GIBS (MODIS Terra & VIIRS SNPP True Color) + Esri World Imagery (High-Res)
- **State**: Pinia
- **Routing**: Vue Router
- **Styling**: Tailwind CSS v4
- **Primitives**: Reka UI
- **Composables**: VueUse
