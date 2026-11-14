import asyncio
import csv
import io
import json
from pathlib import Path

import httpx2

try:
    from pipeline.config import (
        API_BASE_URL,
        COUNTRY_SUMMARY_INDEX_URL,
        FIRMS_MAP_KEY,
        MAPKEY_STATUS_URL,
        META_DIR,
    )
except ImportError:
    from config import (
        API_BASE_URL,
        COUNTRY_SUMMARY_INDEX_URL,
        FIRMS_MAP_KEY,
        MAPKEY_STATUS_URL,
        META_DIR,
    )



async def fetch_csv(
    client: httpx2.AsyncClient, url: str, delimiter: str = ","
) -> list[dict]:
    resp = await client.get(url)
    resp.raise_for_status()
    text = resp.text.strip()
    if (
        not text
        or "Invalid MAP_KEY" in text
        or "exceeded" in text.lower()
        or "Error" in text[:50]
    ):
        raise RuntimeError(f"FIRMS API rejected request ({url}): {text[:200]}")
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def save_atomic(path: Path, data: object) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def save_atomic_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


async def check_budget(client: httpx2.AsyncClient) -> dict:
    resp = await client.get(
        MAPKEY_STATUS_URL,
        params={"MAP_KEY": FIRMS_MAP_KEY},
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()





async def sync_yearly_summaries(
    client: httpx2.AsyncClient,
    csv_path: Path,
    countries_path: Path | None = None,
) -> None:
    if csv_path.exists() and (countries_path is None or countries_path.exists()):
        return

    resp = await client.get(COUNTRY_SUMMARY_INDEX_URL, timeout=30.0)
    resp.raise_for_status()
    text = resp.text.strip()

    if not csv_path.exists():
        save_atomic_text(csv_path, text + "\n")

    if countries_path and not countries_path.exists():
        countries: set[str] = set()
        for row in csv.DictReader(io.StringIO(text)):
            fname = row.get("filename", "")
            if fname.endswith(".csv"):
                parts = fname[:-4].split("_")
                if len(parts) >= 3:
                    country = "_".join(parts[2:])
                    if country != "all_countries":
                        countries.add(country)

        save_atomic(
            countries_path,
            [
                {
                    "name": c.replace("_", " "),
                    "slug": c,
                }
                for c in sorted(countries)
            ],
        )


async def sync_availability(client: httpx2.AsyncClient, path: Path) -> None:
    if path.exists():
        return
    rows = await fetch_csv(
        client, f"{API_BASE_URL}/data_availability/csv/{FIRMS_MAP_KEY}/all"
    )
    save_atomic(
        path,
        {
            r["data_id"]: {"min_date": r["min_date"], "max_date": r["max_date"]}
            for r in rows
        },
    )


async def main() -> None:
    META_DIR.mkdir(parents=True, exist_ok=True)
    summaries_path = META_DIR / "yearly_summary_files.csv"
    countries_path = META_DIR / "countries.json"
    avail_path = META_DIR / "data_availability.json"

    async with httpx2.AsyncClient(
        headers={"User-Agent": "firms-pipeline/1.0"},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        _, _, budget = await asyncio.gather(
            sync_yearly_summaries(client, summaries_path, countries_path),
            sync_availability(client, avail_path),
            check_budget(client),
        )

    print("MAP_KEY status:", budget)
    c = json.loads(countries_path.read_text(encoding="utf-8"))
    a = json.loads(avail_path.read_text(encoding="utf-8"))
    assert any(x["slug"] == "Nicaragua" for x in c), "Missing Nicaragua"
    assert "MODIS_SP" in a, "Missing MODIS_SP"
    assert summaries_path.exists() and summaries_path.stat().st_size > 0, "Missing yearly_summary_files.csv"
    print(
        f"OK: {len(c)} countries, {len(a)} datasets, {summaries_path.name} cached."
    )


if __name__ == "__main__":
    asyncio.run(main())
