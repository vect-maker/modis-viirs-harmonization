import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Cargar variables de entorno desde el primer .env encontrado en los directorios padre
for parent in Path(__file__).resolve().parents:
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        break
else:
    load_dotenv()

database_url = os.getenv("DATABASE_URL")

if database_url:
    # Asegurar driver psycopg
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://") and not database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    connection_string = database_url
else:
    server = os.getenv("DB_SERVER", "localhost")
    port = os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5433"))
    database = os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "firms"))
    username = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "postgres"))
    password = os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "postgres"))
    sslmode = os.getenv("DB_SSLMODE", "prefer")
    connection_string = (
        f"postgresql+psycopg://{username}:{password}"
        f"@{server}:{port}/{database}?sslmode={sslmode}"
    )

engine = create_engine(connection_string)
