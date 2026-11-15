from __future__ import annotations

import uuid

FIRMS_NAMESPACE = uuid.UUID("98b00dc4-63e7-5855-bfed-2cdc66170e68")

CENTRAL_AMERICA_COUNTRIES: tuple[str, ...] = (
    "Belize",
    "Costa_Rica",
    "El_Salvador",
    "Guatemala",
    "Honduras",
    "Nicaragua",
    "Panama",
)

CENTRAL_AMERICA_BBOX = "-92.3,7.2,-77.1,18.5"
DEFAULT_FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov"


def firms_uuid5(name: str) -> uuid.UUID:
    """Return a deterministic UUIDv5 in the FIRMS project namespace."""
    return uuid.uuid5(FIRMS_NAMESPACE, name)
