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
