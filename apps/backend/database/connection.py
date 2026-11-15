import os

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine

# Cargar variables de entorno desde la raíz del proyecto si existe .env
load_dotenv(find_dotenv())

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is required.")

engine = create_engine(database_url)
