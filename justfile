set dotenv-load
set positional-arguments

# List available recipes
default:
    @just --list

# Register application submodules
mod pipeline 'apps/pipeline/justfile'
mod frontend 'apps/frontend/justfile'

# Generate sample hotspot data for frontend from Parquet using DuckDB
sample-data *args:
    just pipeline export-sample {{args}}

# Restore AI agent skills from skills-lock.json
skills-install:
    npx -y skills experimental_install -y -a antigravity codex

# Update all AI agent skills to their latest versions
skills-update:
    npx -y skills update -y

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
db-psql *args:
    psql "$DATABASE_URL" "$@"
