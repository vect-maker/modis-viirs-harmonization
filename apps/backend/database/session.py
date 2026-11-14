from sqlmodel import Session
from .connection import engine

async def get_session():
    with Session(engine) as session:
        yield session