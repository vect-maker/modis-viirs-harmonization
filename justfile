# List available recipes
default:
    @just --list

# Create virtual environment with uv and install dependencies
setup-env:
    uv venv
    uv pip install -r requirements.txt

# Refresh metadata
run-sync-meta:
    uv run pipeline/sync_meta.py
