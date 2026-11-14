from sqlmodel import SQLModel

try:
    from .connection import engine
except ImportError:
    from connection import engine


async def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
