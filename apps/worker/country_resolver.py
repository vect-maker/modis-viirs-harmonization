from __future__ import annotations

import functools
import json
from pathlib import Path

from shapely import Geometry, Point, STRtree, covers, prepare
from shapely.geometry import shape

DEFAULT_GEOJSON_PATH = (
    Path(__file__).resolve().parent / "data" / "central_america.geojson"
)


class CentralAmericaCountryResolver:
    """Resolves (lat, lon) coordinates to one of the 7 Central American countries."""

    def __init__(self, geojson_path: Path | str = DEFAULT_GEOJSON_PATH) -> None:
        path = Path(geojson_path)
        with path.open("r", encoding="utf-8") as fh:
            collection = json.load(fh)

        self._names: list[str] = []
        self._geometries: list[Geometry] = []
        for feature in collection.get("features", []):
            name = str(feature.get("properties", {}).get("name") or "").strip()
            geom_raw = feature.get("geometry")
            if not name or not geom_raw:
                continue
            geom = shape(geom_raw)
            prepare(geom)
            self._names.append(name)
            self._geometries.append(geom)

        self._tree = STRtree(self._geometries)

    def resolve(self, latitude: float, longitude: float) -> str | None:
        """
        Return the Central American country name (e.g. 'Nicaragua', 'Costa_Rica')
        containing (longitude, latitude), or None if outside Central America.
        """
        pt = Point(longitude, latitude)
        for idx in self._tree.query(pt):
            geom = self._geometries[int(idx)]
            if covers(geom, pt):
                return self._names[int(idx)]
        return None


@functools.lru_cache(maxsize=1)
def get_default_country_resolver() -> CentralAmericaCountryResolver:
    return CentralAmericaCountryResolver()
