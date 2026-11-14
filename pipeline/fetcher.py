import argparse
import asyncio
import io
from datetime import UTC, datetime

import httpx2
import pandas as pd
from core.api import check_budget, fetch_csv_bytes
from core.config import RAW_DIR
from core.utils import save_atomic_parquet
from db import ArchiveFile, engine, init_db
from sqlalchemy import func
from sqlmodel import Session, col, select


async def fetch_archive_files(
    country: str | None = None,
    year: int | None = None,
    instrument: str | None = None,
    limit: int = 5,
    fetch_all: bool = False,
    dry_run: bool = False,
) -> None:
    init_db()

    with Session(engine) as session:
        statement = select(ArchiveFile).where(ArchiveFile.status == "pending")

        if country:
            normalized_country = country.strip().replace(" ", "_").lower()
            statement = statement.where(
                func.lower(col(ArchiveFile.country)) == normalized_country
            )
        if year:
            statement = statement.where(ArchiveFile.year == year)
        if instrument:
            normalized_instrument = instrument.strip().replace("_", "-").lower()
            statement = statement.where(
                func.lower(col(ArchiveFile.instrument)) == normalized_instrument
            )

        statement = statement.order_by(
            col(ArchiveFile.year).asc(),
            col(ArchiveFile.country).asc(),
        )

        if not fetch_all and limit > 0:
            statement = statement.limit(limit)

        records = list(session.exec(statement).all())

    if not records:
        print("No pending archive files matching the specified criteria.")
        return

    print(f"Found {len(records)} pending file(s) to process.")
    if dry_run:
        print("[DRY-RUN] Files that would be downloaded:")
        for r in records:
            print(
                f" - {r.instrument}/{r.year}/{r.country.lower()}.parquet ({r.filename})"
            )
        return

    async with httpx2.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        budget = await check_budget(client)
        limit_val = budget.get("transaction_limit", 0)
        curr_val = budget.get("current_transactions", 0)
        print(f"FIRMS API Quota status: {curr_val}/{limit_val} transactions")

        completed_count = 0
        failed_count = 0

        for idx, record in enumerate(records, start=1):
            parquet_filename = f"{record.country.lower()}.parquet"
            dest_path = (
                RAW_DIR / record.instrument / str(record.year) / parquet_filename
            )

            print(
                f"[{idx}/{len(records)}] Fetching {record.filename} "
                f"({record.country}, {record.year})..."
            )

            with Session(engine) as session:
                db_record = session.get(ArchiveFile, record.id)
                if db_record is None:
                    continue

                # Check if local parquet file already exists
                if dest_path.exists() and dest_path.stat().st_size > 0:
                    try:
                        df_existing = pd.read_parquet(dest_path)
                        db_record.status = "completed"
                        db_record.local_filename = parquet_filename
                        db_record.local_format = "parquet"
                        db_record.local_path = str(dest_path)
                        db_record.local_size = dest_path.stat().st_size
                        db_record.row_count = len(df_existing)
                        db_record.downloaded_at = datetime.now(UTC)
                        db_record.error_message = None
                        session.add(db_record)
                        session.commit()
                        completed_count += 1
                        print(f" -> Already exists on disk ({len(df_existing)} rows).")
                        continue
                    except Exception:
                        pass

                try:
                    content = await fetch_csv_bytes(client, record.remote_subpath)
                    df = pd.read_csv(io.BytesIO(content))
                    save_atomic_parquet(df, dest_path)

                    db_record.status = "completed"
                    db_record.local_filename = parquet_filename
                    db_record.local_format = "parquet"
                    db_record.local_path = str(dest_path)
                    db_record.local_size = dest_path.stat().st_size
                    db_record.row_count = len(df)
                    db_record.downloaded_at = datetime.now(UTC)
                    db_record.error_message = None
                    session.add(db_record)
                    session.commit()

                    completed_count += 1
                    print(
                        f" -> Saved to {dest_path.name} "
                        f"({len(df)} rows, {dest_path.stat().st_size} bytes)"
                    )

                except Exception as e:
                    db_record.download_attempts += 1
                    db_record.status = "failed"
                    db_record.error_message = str(e)[:500]
                    session.add(db_record)
                    session.commit()

                    failed_count += 1
                    print(f" -> ERROR fetching {record.filename}: {e}")

        print(
            f"\nFetch batch finished: {completed_count} completed, "
            f"{failed_count} failed."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch NASA FIRMS archive CSVs, convert to Parquet, and track status."
        )
    )
    parser.add_argument(
        "--country",
        type=str,
        default=None,
        help="Filter by country name (e.g. Nicaragua)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Filter by year (e.g. 2000)",
    )
    parser.add_argument(
        "--instrument",
        type=str,
        default=None,
        help="Filter by instrument (modis, viirs-snpp, viirs-jpss1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max files to fetch (default: 5, use 0 or --all for unlimited)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all matching pending files (ignores --limit)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview matching files without downloading",
    )

    args = parser.parse_args()

    asyncio.run(
        fetch_archive_files(
            country=args.country,
            year=args.year,
            instrument=args.instrument,
            limit=args.limit,
            fetch_all=args.all,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
