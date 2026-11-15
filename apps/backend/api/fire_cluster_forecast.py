from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, col, select

from analytics.FireForecastService import compute_cluster_expansion
from database.session import get_session
from model import ClusterHotspots, FireCluster, FireClusterForecast, Hotspots
from repositories.pagination import paginate_statement
from schemas.pagination import PaginatedResponse, PaginationDep

router = APIRouter(prefix="/fire-cluster-forecasts", tags=["FireClusterForecast"])


class ForecastCalculateRequest(BaseModel):
    fireClusterId: int


@router.get("", summary="Listar pronósticos de expansión de clusters")
async def get_fire_cluster_forecasts(
    pagination: PaginationDep,
    session: Session = Depends(get_session),
) -> PaginatedResponse[FireClusterForecast]:
    stmt = select(FireClusterForecast).order_by(col(FireClusterForecast.id))
    return paginate_statement(session, stmt, pagination, FireClusterForecast)


@router.post("/calculate", summary="Calcular y guardar rumbo y velocidad de expansión")
async def calculate_forecast(
    payload: ForecastCalculateRequest,
    session: Session = Depends(get_session),
):
    cluster = session.get(FireCluster, payload.fireClusterId)
    if cluster is None:
        raise HTTPException(status_code=404, detail="FireCluster no encontrado")

    stmt = (
        select(Hotspots)
        .join(ClusterHotspots, col(ClusterHotspots.hotspotsId) == col(Hotspots.id))
        .where(col(ClusterHotspots.clusterId) == payload.fireClusterId)
        .order_by(col(Hotspots.acq_datetime))
    )
    hotspots = session.exec(stmt).all()
    points = [
        (h.latitude, h.longitude, h.acq_datetime)
        for h in hotspots
        if h.latitude is not None
        and h.longitude is not None
        and h.acq_datetime is not None
    ]

    if len(points) < 2:
        raise HTTPException(
            status_code=400,
            detail="El cluster requiere al menos 2 hotspots válidos para calcular expansión",
        )

    metrics = compute_cluster_expansion(points)

    forecast = FireClusterForecast(
        fireClusterId=payload.fireClusterId,
        dirExpansion=float(metrics["dirExpansion"]),
        cardinalDirection=str(metrics["cardinalDirection"]),
        veloExpansion=float(metrics["veloExpansion"]),
        distanceKm=float(metrics["distanceKm"]),
    )
    session.add(forecast)
    session.commit()
    session.refresh(forecast)

    return forecast
