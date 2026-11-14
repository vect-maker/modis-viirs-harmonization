from sqlmodel import SQLModel

import model  # noqa: F401
from .connection import engine


async def create_db_and_tables():
    SQLModel.metadata.create_all(engine)