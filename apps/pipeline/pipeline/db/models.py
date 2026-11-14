from datetime import datetime
from typing import Any

from sqlmodel import Field, SQLModel


class ArchiveFile(SQLModel, table=True):
    __tablename__: Any = "archive_files"

    id: int | None = Field(default=None, primary_key=True)

    # Remote file attributes
    filename: str = Field(unique=True, index=True)
    instrument: str = Field(index=True)
    year: int = Field(index=True)
    country: str = Field(index=True)
    remote_subpath: str
    remote_size: int | None = None
    remote_updated_at: str | None = None

    # Download tracking
    status: str = Field(default="pending", index=True)
    local_filename: str | None = Field(default=None, index=True)
    local_format: str = Field(default="parquet")
    local_path: str | None = None
    local_size: int | None = None
    download_attempts: int = Field(default=0)
    downloaded_at: datetime | None = None
    error_message: str | None = None

    # Ingestion tracking
    ingestion_status: str = Field(default="pending", index=True)
    row_count: int | None = None
    ingested_at: datetime | None = None
