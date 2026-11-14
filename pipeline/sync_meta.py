import asyncio

import httpx2
from api import check_budget, fetch_and_save_csv
from config import (
    COUNTRY_SUMMARY_INDEX_PATH,
    FIRMS_MAP_KEY,
    RAW_META_DIR,
)


async def main() -> None:
    RAW_META_DIR.mkdir(parents=True, exist_ok=True)
    summaries_path = RAW_META_DIR / "yearly_summary_files.csv"
    avail_path = RAW_META_DIR / "data_availability.csv"

    async with httpx2.AsyncClient(
        headers={"User-Agent": "firms-pipeline/1.0"},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        # Check budget BEFORE executing metadata sync
        budget = await check_budget(client)
        print("Initial MAP_KEY budget:", budget)

        # Sync raw metadata CSV files to temp storage using FIRMS subpaths
        await asyncio.gather(
            fetch_and_save_csv(client, COUNTRY_SUMMARY_INDEX_PATH, summaries_path),
            fetch_and_save_csv(
                client,
                f"api/data_availability/csv/{FIRMS_MAP_KEY}/all",
                avail_path,
            ),
        )

    print(f"Saved: {summaries_path} ({summaries_path.stat().st_size} bytes)")
    print(f"Saved: {avail_path} ({avail_path.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
