from sqlmodel import SQLModel


from connection import engine


async def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
