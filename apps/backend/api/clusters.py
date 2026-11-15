from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, func, select

from database.session import get_session
from model import ClusterHotspots, FireCluster
from model.ClusterStatus import ClusterStatus
from repositories.pagination import paginate_statement
from schemas.pagination import PaginatedResponse, PaginationDep

router = APIRouter(prefix="/clusters", tags=["Clusters"])


@router.get("", summary="Listar clusters")
async def get_clusters(
    pagination: PaginationDep,
    status: ClusterStatus | None = Query(default=None, description="Filtrar por estado"),
    session: Session = Depends(get_session),
) -> PaginatedResponse[FireCluster]:
    """
    Lista todos los FireClusters con paginación y filtro opcional por estado.
    """
    stmt = select(FireCluster).order_by(col(FireCluster.id))
    if status is not None:
        stmt = stmt.where(FireCluster.status == status)

    return paginate_statement(session, stmt, pagination, FireCluster)


@router.get("/{cluster_id}", summary="Detalle de un cluster")
async def get_cluster(
    cluster_id: int,
    pagination: PaginationDep,
    session: Session = Depends(get_session),
):
    """
    Retorna un FireCluster con la lista paginada de sus hotspots asociados.
    """
    cluster = session.get(FireCluster, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster no encontrado")

    base_stmt = select(ClusterHotspots).where(ClusterHotspots.clusterId == cluster_id)
    total = session.exec(select(func.count()).select_from(base_stmt.subquery())).one()
    link_stmt = (
        base_stmt.order_by(col(ClusterHotspots.hotspotsId))
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    links = session.exec(link_stmt).all()

    return {
        "data": {
            "cluster": cluster,
            "hotspots": links,
        },
        "total": total,
        "limit": pagination.limit,
        "offset": pagination.offset,
    }
