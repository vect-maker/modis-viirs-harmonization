from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, col, select

from analytics.FireForecastService import compute_cluster_expansion
from database.session import get_session
from model import ClusterHotspots, FireCluster, FireClusterForecast, Hotspots

router = APIRouter(prefix="/fire-cluster-forecasts", tags=["FireClusterForecast"])


class ForecastCalculateRequest(BaseModel):
    fireClusterId: int


@router.get("/", summary="Listar pronósticos de expansión de clusters")
async def get_fire_cluster_forecasts(
    limit: int = Query(default=50, ge=1, le=1000, description="Máximo de elementos a retornar"),
    offset: int = Query(default=0, ge=0, description="Elementos a saltar"),
    session: Session = Depends(get_session),
):
    stmt = select(FireClusterForecast).offset(offset).limit(limit)
    data = session.exec(stmt).all()
    return {
        "data": data,
        "limit": limit,
        "offset": offset,
    }


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
