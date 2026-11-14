from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from database.session import get_session
from model import ClusterHotspots

router = APIRouter(prefix="/cluster-hotspots", tags=["ClusterHotspots"])


@router.get("/", summary="Listar relaciones cluster-hotspot")
async def get_cluster_hotspots(
    limit: int = Query(default=50, ge=1, le=1000, description="Máximo de elementos a retornar"),
    offset: int = Query(default=0, ge=0, description="Elementos a saltar"),
    session: Session = Depends(get_session),
):
    stmt = select(ClusterHotspots).offset(offset).limit(limit)
    data = session.exec(stmt).all()
    return {
        "data": data,
        "limit": limit,
        "offset": offset,
    }
