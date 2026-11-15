import os

from dotenv import find_dotenv, load_dotenv
from shared_core.db import normalize_postgres_url
from sqlalchemy import create_engine

# Cargar variables de entorno desde la raíz del proyecto si existe .env
load_dotenv(find_dotenv())

database_url = os.getenv("DATABASE_URL")

if database_url:
    connection_string = normalize_postgres_url(database_url)
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
