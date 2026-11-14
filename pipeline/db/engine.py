from collections.abc import Generator

from core.config import DATABASE_URL, DB_PATH
from sqlmodel import Session, SQLModel, create_engine

# Ensure parent directory exists for SQLite database file
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Initialize database tables according to SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session."""
    with Session(engine) as session:
        yield session
