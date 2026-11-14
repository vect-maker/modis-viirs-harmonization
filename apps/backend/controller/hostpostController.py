from fastapi import Depends, Session, APIRouter
from database.session import get_session
from repositories.HotspotRepository import HotspotRepository
from sqlmodel import Session

router = APIRouter(
    prefix="/hostpost",
    tags=["Hostpost"]
)

@router.get("/")
async def get_hotspots(session: Session = Depends(get_session)):
    repository = HotspotRepository(session)
    return repository.get_hotspots()


