from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database.session import get_session
from model import ClusterHotspots, FireCluster
from model.ClusterStatus import ClusterStatus

router = APIRouter(prefix="/clusters", tags=["Clusters"])


@router.get("/", summary="Listar clusters")
async def get_clusters(
    limit: int = Query(default=50, ge=1, le=1000, description="Máx. elementos a retornar"),
    offset: int = Query(default=0, ge=0, description="Elementos a saltar"),
    status: ClusterStatus | None = Query(default=None, description="Filtrar por estado"),
    session: Session = Depends(get_session),
):
    """
    Lista todos los FireClusters con paginación y filtro opcional por estado.
    """
    stmt = select(FireCluster)
    if status is not None:
        stmt = stmt.where(FireCluster.status == status)
    stmt = stmt.offset(offset).limit(limit)

    clusters = session.exec(stmt).all()
    return {
        "data": clusters,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{cluster_id}", summary="Detalle de un cluster")
async def get_cluster(
    cluster_id: int,
    limit: int = Query(default=50, ge=1, le=1000, description="Máx. hotspots a retornar"),
    offset: int = Query(default=0, ge=0, description="Hotspots a saltar"),
    session: Session = Depends(get_session),
):
    """
    Retorna un FireCluster con la lista paginada de sus hotspots asociados.
    """
    cluster = session.get(FireCluster, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster no encontrado")

    link_stmt = (
        select(ClusterHotspots)
        .where(ClusterHotspots.clusterId == cluster_id)
        .offset(offset)
        .limit(limit)
    )
    links = session.exec(link_stmt).all()

    return {
        "data": {
            "cluster": cluster,
            "hotspots": links,
        },
        "limit": limit,
        "offset": offset,
    }
