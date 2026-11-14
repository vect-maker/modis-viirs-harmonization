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
