from __future__ import annotations


def normalize_postgres_url(database_url: str) -> str:
    """Ensure PostgreSQL URLs use the psycopg v3 SQLAlchemy driver."""
    url = database_url.strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and not url.startswith(
        "postgresql+psycopg://"
    ):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url
