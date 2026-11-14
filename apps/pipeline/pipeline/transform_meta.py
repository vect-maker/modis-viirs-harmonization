from pathlib import Path
from typing import Any

import pandas as pd
from core.config import RAW_META_DIR
from db import ArchiveFile, engine, init_db
from sqlmodel import Session, select


def transform_and_load_archive_files(raw_csv_path: Path) -> dict[str, int]:
    """Parse yearly summary files with pandas and populate the SQLite database.

    Follows Option 1 idempotency:
    - Inserts new files as 'pending'.
    - Preserves existing files and their pipeline download tracking state.
    """
    if not raw_csv_path.exists():
        raise FileNotFoundError(
            f"Raw metadata file not found at {raw_csv_path}. "
            "Run 'just sync-meta' first."
        )

    #  Read raw CSV with pandas
    df = pd.read_csv(raw_csv_path)

    # Filter for country CSV files (ignoring .zip archives and .txt readmes)
    csv_df = df[df["filename"].str.endswith(".csv")]

    #  Extract and parse attributes
    filenames = [str(x) for x in csv_df["filename"]]
    sizes = [int(x) for x in csv_df["size"]]
    updates = [str(x) for x in csv_df["updated"]]

    records: list[dict[str, Any]] = []
    for fname, size, updated in zip(filenames, sizes, updates, strict=True):
        parts = fname[:-4].split("_", 2)
        instrument = parts[0]
        year = int(parts[1])
        country = parts[2]
        remote_subpath = f"data/country/{instrument}/{year}/{fname}"

        records.append(
            {
                "filename": fname,
                "instrument": instrument,
                "year": year,
                "country": country,
                "remote_subpath": remote_subpath,
                "remote_size": size,
                "remote_updated_at": updated,
            }
        )

    # Upsert into database using SQLModel
    init_db()

    inserted_count = 0
    updated_count = 0
    unchanged_count = 0

    with Session(engine) as session:
        # Load existing files into memory for fast lookup
        existing_records = {
            f.filename: f for f in session.exec(select(ArchiveFile)).all()
        }

        new_records: list[ArchiveFile] = []

        for row in records:
            filename = str(row["filename"])
            row_remote_size = int(row["remote_size"])
            row_remote_updated = str(row["remote_updated_at"])

            if filename in existing_records:
                existing = existing_records[filename]
                changed = False
                if existing.remote_size != row_remote_size:
                    existing.remote_size = row_remote_size
                    changed = True
                if existing.remote_updated_at != row_remote_updated:
                    existing.remote_updated_at = row_remote_updated
                    changed = True

                if changed:
                    session.add(existing)
                    updated_count += 1
                else:
                    unchanged_count += 1
            else:
                new_file = ArchiveFile(
                    filename=filename,
                    instrument=str(row["instrument"]),
                    year=int(row["year"]),
                    country=str(row["country"]),
                    remote_subpath=str(row["remote_subpath"]),
                    remote_size=row_remote_size,
                    remote_updated_at=row_remote_updated,
                    status="pending",
                    ingestion_status="pending",
                )
                new_records.append(new_file)
                inserted_count += 1

        if new_records:
            session.add_all(new_records)
        session.commit()

    return {
        "total_parsed": len(records),
        "inserted": inserted_count,
        "updated": updated_count,
        "unchanged": unchanged_count,
    }


def main() -> None:
    raw_path = RAW_META_DIR / "yearly_summary_files.csv"
    print(f"Transforming {raw_path}...")
    stats = transform_and_load_archive_files(raw_path)
    print(
        f"Done: {stats['total_parsed']} files parsed | "
        f"{stats['inserted']} inserted | "
        f"{stats['updated']} updated | "
        f"{stats['unchanged']} unchanged."
    )


if __name__ == "__main__":
    main()
