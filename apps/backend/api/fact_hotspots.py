from fastapi import APIRouter, Depends
from sqlmodel import Session

from database.session import get_session
from model.StarSchema import HotspotPublic
from repositories.HotspotRepository import HotspotRepository
from schemas.pagination import PaginatedResponse, PaginationDep

router = APIRouter(prefix="/fact-hotspots", tags=["FactHotspots"])


@router.get("/", summary="Listar registros de fact_hotspots")
async def get_fact_hotspots(
    pagination: PaginationDep,
    session: Session = Depends(get_session),
) -> PaginatedResponse[HotspotPublic]:
    return HotspotRepository(session).get_hotspots(pagination)
