from fastapi import APIRouter, Depends
from sqlmodel import Session
from repositories.HotspotRepository import HotspotRepository
from database.session import get_session


router = APIRouter(
    prefix="/hostpost",
    tags=["Hostpost"],
)


@router.get("/")
async def get_hotspots(session: Session = Depends(get_session)):
    repository = HotspotRepository(session)
    return repository.get_hotspots()


@router.get("/dates")
async def get_hotspots_by_dates(
    start_date: str,
    end_date: str,
    session: Session = Depends(get_session),
):
    repository = HotspotRepository(session)
    return repository.get_hostspot_by_dates(start_date, end_date)


@router.get("/location")
async def get_hotspots_by_location(
    latitude: float,
    longitude: float,
    session: Session = Depends(get_session),
):
    repository = HotspotRepository(session)
    return repository.get_hostspot_by_location(latitude, longitude)
