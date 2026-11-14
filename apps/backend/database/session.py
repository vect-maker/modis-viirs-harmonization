from sqlmodel import Session

try:
    from .connection import engine
except ImportError:
    from connection import engine


async def get_session():
    with Session(engine) as session:
        yield session
