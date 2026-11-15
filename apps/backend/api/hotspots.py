from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from database.session import get_session
from repositories.HotspotRepository import HotspotRepository

router = APIRouter(prefix="/hotspots", tags=["Hotspots"])


@router.get("/")
async def get_hotspots(
    limit: int = Query(default=50, ge=1, le=1000, description="Número máximo de elementos a retornar"),
    offset: int = Query(default=0, ge=0, description="Número de elementos a saltar"),
    session: Session = Depends(get_session),
):
    repository = HotspotRepository(session)
    data = repository.get_hotspots(limit=limit, offset=offset)
    return {
        "data": data,
        "limit": limit,
        "offset": offset,
    }
