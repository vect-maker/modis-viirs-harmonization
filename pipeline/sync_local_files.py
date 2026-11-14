from datetime import UTC, datetime
from pathlib import Path

from core.config import RAW_DIR
from db import ArchiveFile, engine, init_db
from sqlmodel import Session, select


def get_dest_path(base_dir: Path, record: ArchiveFile) -> Path:
    safe_country = (
        record.country.lower().replace(" ", "_").replace("'", "").replace('"', "")
    )
    dest_path = (
        base_dir / record.instrument / str(record.year) / f"{safe_country}.parquet"
    )
    return dest_path


def sync_local_files() -> None:
    init_db()

    updated = 0
    with Session(engine) as session:
        statement = select(ArchiveFile).where(ArchiveFile.status != "completed")
        records = session.exec(statement).all()

        for record in records:
            dest_path = get_dest_path(RAW_DIR, record)
            if dest_path.exists() and dest_path.stat().st_size > 0:
                record.status = "completed"
                record.local_filename = dest_path.name
                record.local_format = "parquet"
                record.local_path = str(dest_path)
                record.local_size = dest_path.stat().st_size
                record.downloaded_at = datetime.now(UTC)
                record.error_message = None
                session.add(record)
                updated += 1

        session.commit()

    print(f"Synchronized {updated} existing raw Parquet files with pipeline.db.")


if __name__ == "__main__":
    sync_local_files()
