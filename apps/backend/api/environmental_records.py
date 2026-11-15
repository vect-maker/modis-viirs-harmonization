from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from database.session import get_session
from model import EnvironmentalRecord

router = APIRouter(prefix="/environmental-records", tags=["EnvironmentalRecords"])


@router.get("/", summary="Listar registros ambientales")
async def get_environmental_records(
    limit: int = Query(default=50, ge=1, le=1000, description="Máximo de elementos a retornar"),
    offset: int = Query(default=0, ge=0, description="Elementos a saltar"),
    session: Session = Depends(get_session),
):
    stmt = select(EnvironmentalRecord).offset(offset).limit(limit)
    data = session.exec(stmt).all()
    return {
        "data": data,
        "limit": limit,
        "offset": offset,
    }
