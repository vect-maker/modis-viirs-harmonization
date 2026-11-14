from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import text
from sqlmodel import Session, select

from model import Hotspots


class HotspotRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_hotspots(self, limit: int = 50, offset: int = 0) -> list[Hotspots]:
        statement = select(Hotspots).offset(offset).limit(limit)
        return list(self.session.exec(statement).all())

    def iter_hotspots_filtered(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        batch_size: int = 2000,
        max_rows: int = 50000,
    ) -> Iterator[dict]:
        """
        Lee hotspots desde PostgreSQL por lotes (stream_results/yield_per) con
        filtros de rango temporal y bounding box geográfico para no saturar memoria.
        Solo selecciona las columnas requeridas para análisis espaciotemporal.
        """
        conditions: list[str] = ["latitude IS NOT NULL", "longitude IS NOT NULL", "acq_datetime IS NOT NULL"]
        params: dict[str, object] = {"max_rows": max_rows}

        if start_date is not None:
            conditions.append("acq_datetime >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            conditions.append("acq_datetime <= :end_date")
            params["end_date"] = end_date
        if min_lat is not None:
            conditions.append("latitude >= :min_lat")
            params["min_lat"] = min_lat
        if max_lat is not None:
            conditions.append("latitude <= :max_lat")
            params["max_lat"] = max_lat
        if min_lon is not None:
            conditions.append("longitude >= :min_lon")
            params["min_lon"] = min_lon
        if max_lon is not None:
            conditions.append("longitude <= :max_lon")
            params["max_lon"] = max_lon

        where_clause = " AND ".join(conditions)
        query = text(
            f"""
            SELECT id, latitude, longitude, acq_datetime, frp
            FROM hotspots
            WHERE {where_clause}
            ORDER BY acq_datetime ASC
            LIMIT :max_rows
            """
        ).execution_options(stream_results=True, yield_per=batch_size)

        result = self.session.execute(query, params).mappings()
        for row in result:
            yield dict(row)
