import os

from sqlalchemy import create_engine

server = os.getenv("DB_SERVER", "firms-db-nasa-apps.postgres.database.azure.com")
database = os.getenv("DB_NAME", "postgres")
username = os.getenv("DB_USER", "ocelot")
password = os.getenv("DB_PASSWORD", "Minecraft5")

connection_string = (
    f"postgresql+psycopg://{username}:{password}"
    f"@{server}:5432/{database}?sslmode=require"
)

engine = create_engine(connection_string)