from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlmodel import Session

from database.session import get_session

router = APIRouter(prefix="/countries", tags=["Countries"])


@router.get("/", summary="Listar países (dim_country)")
async def get_countries(
    limit: int = Query(default=50, ge=1, le=1000, description="Máximo de elementos a retornar"),
    offset: int = Query(default=0, ge=0, description="Elementos a saltar"),
    session: Session = Depends(get_session),
):
    stmt = text("SELECT id, name FROM dim_country ORDER BY name OFFSET :offset LIMIT :limit")
    rows = session.execute(stmt, {"limit": limit, "offset": offset}).mappings().all()
    return {
        "data": [dict(row) for row in rows],
        "limit": limit,
        "offset": offset,
    }
