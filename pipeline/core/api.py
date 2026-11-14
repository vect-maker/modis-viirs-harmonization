import asyncio
from pathlib import Path

import httpx2

from core.config import BASE_URL, FIRMS_MAP_KEY, MAPKEY_STATUS_URL
from core.utils import save_atomic_text


async def check_budget(client: httpx2.AsyncClient) -> dict:
    resp = await client.get(
        MAPKEY_STATUS_URL,
        params={"MAP_KEY": FIRMS_MAP_KEY},
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()


async def wait_for_budget(
    client: httpx2.AsyncClient, poll_interval: float = 60.0
) -> dict:
    while True:
        budget = await check_budget(client)
        limit = budget.get("transaction_limit", 0)
        current = budget.get("current_transactions", 0)
        if current < limit:
            return budget
        print(
            f"FIRMS API quota exhausted ({current}/{limit}). "
            f"Waiting {poll_interval}s..."
        )
        await asyncio.sleep(poll_interval)


async def fetch_and_save_csv(
    client: httpx2.AsyncClient,
    subpath: str,
    save_path: Path,
    max_retries: int = 3,
) -> Path:
    url = f"{BASE_URL}/{subpath.lstrip('/')}"

    for attempt in range(max_retries):
        try:
            resp = await client.get(url, timeout=30.0)
            resp.raise_for_status()
            text = resp.text.strip()

            if "Invalid MAP_KEY" in text:
                raise RuntimeError(
                    f"FIRMS rejected request - invalid map key: {text[:200]}"
                )

            if "exceeded" in text.lower():
                print(f"Quota exceeded when requesting {url}. Awaiting budget...")
                await wait_for_budget(client)
                continue

            if not text or (
                "text/html" in resp.headers.get("content-type", "")
                and "<html" in text.lower()
            ):
                raise RuntimeError(f"Unexpected response from {url}: {text[:200]}")

            save_atomic_text(save_path, text + "\n")
            return save_path

        except httpx2.HTTPStatusError as e:
            if e.response.status_code == 429:
                print(f"HTTP 429 received from {url}. Awaiting budget...")
                await wait_for_budget(client)
                continue
            if attempt == max_retries - 1:
                raise
        except Exception:
            if attempt == max_retries - 1:
                raise

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts.")
