set dotenv-load
set positional-arguments

# List available recipes
default:
    @just --list

# Register application submodules
mod pipeline 'apps/pipeline/justfile'
mod backend 'apps/backend/justfile'
mod frontend 'apps/frontend/justfile'
mod report 'apps/report/justfile'

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
    podman compose up -d db

# Stop PostgreSQL + PostGIS container
db-down:
    podman compose down

# Follow database container logs
db-logs:
    podman compose logs -f db

# Open psql shell using DATABASE_URL (local or remote Azure DB)
db-psql *args:
    psql "$DATABASE_URL" "$@"

# Start all services in production mode via Podman Compose
up *args="":
    podman compose up -d {{args}}

# Start all services in debug/dev mode via Podman Compose
up-debug *args="":
    podman compose -f compose.yml -f debug.compose.yml up -d {{args}}

# Build and start all services in production mode
up-build *args="":
    podman compose up -d --build {{args}}

# Build and start all services in debug/dev mode
up-build-debug *args="":
    podman compose -f compose.yml -f debug.compose.yml up -d --build {{args}}

# Stop all compose services
down *args="":
    podman compose down {{args}}

# Follow compose logs (all or specific service)
logs *args="":
    podman compose logs -f {{args}}
