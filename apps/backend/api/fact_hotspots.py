from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlmodel import Session

from database.session import get_session

router = APIRouter(prefix="/fact-hotspots", tags=["FactHotspots"])


@router.get("/", summary="Listar registros de fact_hotspots")
async def get_fact_hotspots(
    limit: int = Query(default=50, ge=1, le=1000, description="Máximo de elementos a retornar"),
    offset: int = Query(default=0, ge=0, description="Elementos a saltar"),
    session: Session = Depends(get_session),
):
    stmt = text(
        """
        SELECT
            id,
            country_id,
            platform_id,
            latitude,
            longitude,
            acq_datetime,
            bright_mir,
            bright_tir,
            scan,
            track,
            confidence,
            confidence_class,
            frp,
            daynight,
            type,
            version
        FROM fact_hotspots
        ORDER BY acq_datetime DESC
        OFFSET :offset LIMIT :limit
        """
    )
    rows = session.execute(stmt, {"limit": limit, "offset": offset}).mappings().all()
    return {
        "data": [dict(row) for row in rows],
        "limit": limit,
        "offset": offset,
    }
