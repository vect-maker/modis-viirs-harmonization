set dotenv-load

# List available recipes
default:
    @just --list

# Create virtual environment with uv and install dependencies
setup-env:
    uv venv
    uv pip install -r requirements.txt

# Refresh metadata
sync-meta:
    uv run pipeline/sync_meta.py

# Transform metadata
transform-meta:
    uv run pipeline/transform_meta.py

# Reset database and re-populate metadata from scratch
reset-db:
    rm -f data/pipeline.db
    uv run pipeline/transform_meta.py

# Fetch archive files from NASA FIRMS and convert to Parquet
fetch-data *args:
    uv run pipeline/fetcher.py {{args}}

# Fuse raw archive Parquet files into a unified Silver dataset
fuse-data:
    mkdir -p data/processed data/temp/duckdb
    duckdb -dark-mode -f sql/fuse_datasets.sql

# Run spatial harmonization feasibility benchmark
benchmark-spatial:
    duckdb -dark-mode -f sql/test_spatial_harmonization.sql

# Start PostgreSQL + PostGIS via Podman Compose
db-up:
    podman compose up -d

# Stop PostgreSQL + PostGIS container
db-down:
    podman compose down

# Follow database container logs
db-logs:
    podman compose logs -f db

# Open psql shell using DATABASE_URL (local or remote Azure DB)
db-psql *cmd:
    psql "$DATABASE_URL" {{cmd}}

# Apply PostGIS schema to PostgreSQL database using DATABASE_URL
db-schema:
    psql "$DATABASE_URL" -f sql/schema_postgis.sql

# Ingest Nicaragua dev dataset from Parquet into PostGIS via DuckDB
db-load-nicaragua:
    duckdb -dark-mode -f sql/load_nicaragua_sample.sql

# Full reset and reload of dev database
db-reset-load: db-schema db-load-nicaragua

# Auto-format and auto-fix pipeline code
format:
    uv run ruff format pipeline
    uv run ruff check --fix pipeline

# Lint pipeline code with ruff
lint:
    uv run ruff check pipeline

# Type-check pipeline code with basedpyright
typecheck:
    uv run basedpyright pipeline
