from sqlalchemy import create_engine

server = "firms-db-nasa-apps.postgres.database.azure.com"
database = "postgres"
username = "ocelot"
password = "Minecraft5"

connection_string = (
    f"postgresql+psycopg://{username}:{password}"
    f"@{server}:5432/{database}?sslmode=require"
)

engine = create_engine(connection_string)