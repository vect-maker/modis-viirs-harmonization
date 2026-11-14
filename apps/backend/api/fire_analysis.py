from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session

from analytics.FireClusterer import FireClusterer
from analytics.FireMovementAnalyzer import FireMovementAnalyzer
from analytics.FirePredictor import FirePredictor, build_training_dataset
from analytics.HotspotProcessor import HotspotProcessor
from analytics.WeatherAnalyzer import WeatherAnalyzer
from database.session import get_session
from enviromental.RequestWeather import RequestWeather
from enviromental.WeatherDataClient import WeatherClientError, WeatherDataClient
from repositories.HotspotRepository import HotspotRepository

router = APIRouter(prefix="/analysis", tags=["FireAnalysis"])


class ClusterMovementRequest(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    max_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    min_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    max_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    eps_km: float = Field(default=1.0, gt=0.0)
    min_samples: int = Field(default=2, ge=1)
    time_window_hours: float = Field(default=24.0, gt=0.0)
    max_time_window_hours: float = Field(default=72.0, gt=0.0)
    interval_hours: float = Field(default=6.0, gt=0.0)
    max_rows: int = Field(default=20000, ge=1, le=100000)


class WeatherCorrelationRequest(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    start_date: datetime
    end_date: datetime
    fire_direction_deg: float | None = Field(default=None, ge=0.0, lt=360.0)


class FirePredictRequest(ClusterMovementRequest):
    min_training_samples: int = Field(default=20, ge=5)
    test_ratio: float = Field(default=0.2, gt=0.0, lt=0.9)
    n_estimators: int = Field(default=100, ge=10, le=500)


@router.post("/cluster-movement", summary="Agrupar hotspots y analizar movimiento por intervalos")
async def analyze_clusters_and_movement(
    payload: ClusterMovementRequest,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    repo = HotspotRepository(session)
    rows_iter = repo.iter_hotspots_filtered(
        start_date=payload.start_date,
        end_date=payload.end_date,
        min_lat=payload.min_lat,
        max_lat=payload.max_lat,
        min_lon=payload.min_lon,
        max_lon=payload.max_lon,
        max_rows=payload.max_rows,
    )

    processor = HotspotProcessor()
    prepared = processor.prepare(rows_iter)
    if prepared.is_empty:
        return {
            "summary": {"hotspots_valid": 0, "clusters": 0, "noise": 0},
            "data": [],
            "limit": limit,
            "offset": offset,
        }

    try:
        clusterer = FireClusterer(
            eps_km=payload.eps_km,
            min_samples=payload.min_samples,
            time_window_hours=payload.time_window_hours,
            max_time_window_hours=payload.max_time_window_hours,
        )
        clustering = clusterer.fit_predict(prepared)
        analyzer = FireMovementAnalyzer(interval_hours=payload.interval_hours)
        trajectories = analyzer.analyze_all(prepared, clustering.labels)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    serialized_fires = [
        {
            "fire_id": fire_id,
            "steps": [asdict(step) for step in steps],
        }
        for fire_id, steps in trajectories.items()
    ]

    return {
        "summary": {
            "hotspots_valid": len(prepared),
            "hotspots_dropped": prepared.dropped_count,
            "clusters": clustering.cluster_count,
            "noise": clustering.noise_count,
        },
        "data": serialized_fires[offset : offset + limit],
        "limit": limit,
        "offset": offset,
    }


@router.post("/weather-correlation", summary="Analizar vectores de viento NASA POWER y alineación con el fuego")
async def analyze_weather_correlation(
    payload: WeatherCorrelationRequest,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    client = WeatherDataClient()
    req = RequestWeather(
        latitude=payload.latitude,
        longitude=payload.longitude,
        start=payload.start_date,
        end=payload.end_date,
    )
    try:
        daily_records = await client.fetch_daily_records(req)
    except WeatherClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    analyzer = WeatherAnalyzer()
    results = [
        {"date": rec.get("date"), **asdict(analyzer.analyze(rec, payload.fire_direction_deg))}
        for rec in daily_records
    ]

    return {
        "data": results[offset : offset + limit],
        "limit": limit,
        "offset": offset,
    }


@router.post("/predict", summary="Entrenar RandomForest, evaluar y predecir desplazamiento futuro")
async def predict_fire_displacement(
    payload: FirePredictRequest,
    session: Session = Depends(get_session),
):
    repo = HotspotRepository(session)
    rows_iter = repo.iter_hotspots_filtered(
        start_date=payload.start_date,
        end_date=payload.end_date,
        min_lat=payload.min_lat,
        max_lat=payload.max_lat,
        min_lon=payload.min_lon,
        max_lon=payload.max_lon,
        max_rows=payload.max_rows,
    )

    prepared = HotspotProcessor().prepare(rows_iter)
    if prepared.is_empty:
        raise HTTPException(status_code=422, detail="No hay hotspots válidos en el rango indicado.")

    clusterer = FireClusterer(
        eps_km=payload.eps_km,
        min_samples=payload.min_samples,
        time_window_hours=payload.time_window_hours,
        max_time_window_hours=payload.max_time_window_hours,
    )
    clustering = clusterer.fit_predict(prepared)
    trajectories = FireMovementAnalyzer(interval_hours=payload.interval_hours).analyze_all(
        prepared, clustering.labels
    )

    all_steps = [step for steps in trajectories.values() for step in steps]
    if len(all_steps) < 2:
        raise HTTPException(status_code=422, detail="Trayectorias insuficientes para análisis meteorológico y predicción.")

    # Consultar clima diario en NASA POWER usando centroide global y rango de fechas observado
    min_dt = min(s.timestamp for s in all_steps)
    max_dt = max(s.timestamp for s in all_steps)
    mean_lat = sum(s.centroid_lat for s in all_steps) / len(all_steps)
    mean_lon = sum(s.centroid_lon for s in all_steps) / len(all_steps)

    weather_client = WeatherDataClient()
    try:
        daily_records = await weather_client.fetch_daily_records(
            RequestWeather(latitude=mean_lat, longitude=mean_lon, start=min_dt, end=max_dt)
        )
    except WeatherClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    weather_by_date = {rec["date"]: rec for rec in daily_records if "date" in rec}
    weather_analyzer = WeatherAnalyzer()
    weather_map = {}
    for fire_id, steps in trajectories.items():
        for step in steps:
            date_key = step.timestamp.strftime("%Y%m%d")
            w_rec = weather_by_date.get(date_key)
            weather_map[(fire_id, step.timestamp)] = weather_analyzer.analyze(
                w_rec, fire_direction_deg=step.direction_deg
            )

    dataset = build_training_dataset(trajectories, weather_map)
    predictor = FirePredictor(
        n_estimators=payload.n_estimators,
        min_training_samples=payload.min_training_samples,
    )
    try:
        metrics = predictor.train_and_evaluate(dataset, test_ratio=payload.test_ratio)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Predecir desplazamiento futuro usando la última observación válida
    last_features = dataset.X[-1]
    prediction = predictor.predict(last_features)

    return {
        "metrics": asdict(metrics),
        "latest_prediction": asdict(prediction),
    }
