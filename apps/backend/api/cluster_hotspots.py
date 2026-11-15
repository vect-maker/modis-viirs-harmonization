from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from database.session import get_session
from model import ClusterHotspots
from repositories.pagination import paginate_statement
from schemas.pagination import PaginatedResponse, PaginationDep

router = APIRouter(prefix="/cluster-hotspots", tags=["ClusterHotspots"])


@router.get("", summary="Listar relaciones cluster-hotspot")
async def get_cluster_hotspots(
    pagination: PaginationDep,
    session: Session = Depends(get_session),
) -> PaginatedResponse[ClusterHotspots]:
    stmt = select(ClusterHotspots).order_by(
        col(ClusterHotspots.clusterId),
        col(ClusterHotspots.hotspotsId),
    )
    return paginate_statement(session, stmt, pagination, ClusterHotspots)
