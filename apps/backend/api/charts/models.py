from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from analytics.DashboardAnalytics import run_monthly_seasonal_forecast
from analytics.FireClusterer import FireClusterer
from analytics.FireMovementAnalyzer import FireMovementAnalyzer
from analytics.FirePredictor import FirePredictor, build_training_dataset
from analytics.HotspotProcessor import HotspotProcessor
from analytics.WeatherAnalyzer import WeatherAnalyzer
from database.session import get_session
from enviromental.RequestWeather import RequestWeather
from enviromental.WeatherDataClient import WeatherClientError, WeatherDataClient
from repositories.DashboardRepository import DashboardRepository
from repositories.HotspotRepository import HotspotRepository
from repositories.pagination import paginate_sequence
from schemas.charts import ChartFiltersDep, ChartResponse, build_chart_response
from schemas.pagination import PaginationDep

router = APIRouter(prefix="/models", tags=["Charts - Models"])


@router.get(
    "/monthly-forecast",
    response_model=ChartResponse[dict[str, Any]],
    summary="Pronóstico estacional mensual con intervalos de confianza y métricas de error",
)
async def get_monthly_forecast(
    filters: ChartFiltersDep,
    train_ratio: Annotated[float, Query(gt=0.5, lt=0.95)] = 0.8,
    future_months: Annotated[int, Query(ge=1, le=24)] = 6,
    start_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    session: Session = Depends(get_session),
) -> ChartResponse[dict[str, Any]]:
    filter_start_yr, filter_end_yr = filters.to_year_bounds()
    eff_start_year = start_year if start_year is not None else filter_start_yr
    eff_end_year = end_year if end_year is not None else filter_end_yr

    if eff_start_year is not None and eff_end_year is not None and eff_start_year > eff_end_year:
        raise HTTPException(
            status_code=400, detail="start_year debe ser menor o igual a end_year"
        )
    repo = DashboardRepository(session)
    monthly = repo.get_monthly_counts(
        start_year=eff_start_year,
        end_year=eff_end_year,
        metric=filters.metric,
        country=filters.country,
        polygon_wkt=filters.polygon_wkt,
    )
    if len(monthly) < 18:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 18 meses de datos para generar el pronóstico estacional",
        )

    months = [str(r["month_key"]) for r in monthly]
    counts = [float(r["value"]) for r in monthly]
    try:
        payload = run_monthly_seasonal_forecast(
            months=months,
            counts=counts,
            train_ratio=train_ratio,
            future_months=future_months,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_chart_response(
        "models.monthly-forecast",
        payload,
        filters,
        extra_filters={
            "train_ratio": train_ratio,
            "future_months": future_months,
            "start_year": eff_start_year,
            "end_year": eff_end_year,
        },
    )


@router.get(
    "/cluster-movement",
    response_model=ChartResponse[dict[str, Any]],
    summary="Agrupar hotspots y analizar movimiento por intervalos",
)
async def get_cluster_movement(
    filters: ChartFiltersDep,
    pagination: PaginationDep,
    min_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    max_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    min_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    max_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    eps_km: Annotated[float, Query(gt=0.0)] = 1.0,
    min_samples: Annotated[int, Query(ge=1)] = 2,
    time_window_hours: Annotated[float, Query(gt=0.0)] = 24.0,
    max_time_window_hours: Annotated[float, Query(gt=0.0)] = 72.0,
    interval_hours: Annotated[float, Query(gt=0.0)] = 6.0,
    max_rows: Annotated[int, Query(ge=1, le=100000)] = 20000,
    session: Session = Depends(get_session),
) -> ChartResponse[dict[str, Any]]:
    start_dt, end_dt = filters.to_datetime_bounds()
    polygon_wkt = filters.polygon_wkt
    repo = HotspotRepository(session)
    stmt_kwargs: dict[str, Any] = {}
    if filters.country is not None:
        stmt_kwargs["country"] = filters.country
    if polygon_wkt is not None:
        stmt_kwargs["polygon_wkt"] = polygon_wkt

    rows_iter = repo.iter_hotspots_filtered(
        start_date=start_dt,
        end_date=end_dt,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        max_rows=max_rows,
        **stmt_kwargs,
    )

    prepared = HotspotProcessor().prepare(rows_iter)
    if prepared.is_empty:
        return build_chart_response(
            "models.cluster-movement",
            {
                "summary": {"hotspots_valid": 0, "clusters": 0, "noise": 0},
                "fires": [],
                "total": 0,
                "limit": pagination.limit,
                "offset": pagination.offset,
            },
            filters,
            extra_filters={
                "eps_km": eps_km,
                "min_samples": min_samples,
                "interval_hours": interval_hours,
            },
        )

    try:
        clusterer = FireClusterer(
            eps_km=eps_km,
            min_samples=min_samples,
            time_window_hours=time_window_hours,
            max_time_window_hours=max_time_window_hours,
        )
        clustering = clusterer.fit_predict(prepared)
        analyzer = FireMovementAnalyzer(interval_hours=interval_hours)
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
    paginated = paginate_sequence(serialized_fires, pagination)

    return build_chart_response(
        "models.cluster-movement",
        {
            "summary": {
                "hotspots_valid": len(prepared),
                "hotspots_dropped": prepared.dropped_count,
                "clusters": clustering.cluster_count,
                "noise": clustering.noise_count,
            },
            "fires": paginated.data,
            "total": paginated.total,
            "limit": paginated.limit,
            "offset": paginated.offset,
        },
        filters,
        extra_filters={
            "eps_km": eps_km,
            "min_samples": min_samples,
            "time_window_hours": time_window_hours,
            "max_time_window_hours": max_time_window_hours,
            "interval_hours": interval_hours,
            "max_rows": max_rows,
        },
    )


@router.get(
    "/weather-correlation",
    response_model=ChartResponse[dict[str, Any]],
    summary="Analizar vectores de viento NASA POWER y alineación con el fuego",
)
async def get_weather_correlation(
    filters: ChartFiltersDep,
    pagination: PaginationDep,
    latitude: Annotated[float, Query(ge=-90.0, le=90.0)],
    longitude: Annotated[float, Query(ge=-180.0, le=180.0)],
    fire_direction_deg: Annotated[float | None, Query(ge=0.0, lt=360.0)] = None,
) -> ChartResponse[dict[str, Any]]:
    start_dt, end_dt = filters.to_datetime_bounds()
    if start_dt is None or end_dt is None:
        raise HTTPException(
            status_code=422,
            detail="start_date y end_date son requeridos para weather-correlation",
        )

    client = WeatherDataClient()
    req = RequestWeather(
        latitude=latitude,
        longitude=longitude,
        start=start_dt,
        end=end_dt,
    )
    try:
        daily_records = await client.fetch_daily_records(req)
    except WeatherClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    analyzer = WeatherAnalyzer()
    results = [
        {
            "date": rec.get("date"),
            **asdict(analyzer.analyze(rec, fire_direction_deg)),
        }
        for rec in daily_records
    ]
    paginated = paginate_sequence(results, pagination)

    return build_chart_response(
        "models.weather-correlation",
        {
            "records": paginated.data,
            "total": paginated.total,
            "limit": paginated.limit,
            "offset": paginated.offset,
        },
        filters,
        extra_filters={
            "latitude": latitude,
            "longitude": longitude,
            "fire_direction_deg": fire_direction_deg,
        },
    )


@router.get(
    "/predict",
    response_model=ChartResponse[dict[str, Any]],
    summary="Entrenar RandomForest, evaluar y predecir desplazamiento futuro",
)
async def get_fire_displacement_prediction(
    filters: ChartFiltersDep,
    min_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    max_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    min_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    max_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    eps_km: Annotated[float, Query(gt=0.0)] = 1.0,
    min_samples: Annotated[int, Query(ge=1)] = 2,
    time_window_hours: Annotated[float, Query(gt=0.0)] = 24.0,
    max_time_window_hours: Annotated[float, Query(gt=0.0)] = 72.0,
    interval_hours: Annotated[float, Query(gt=0.0)] = 6.0,
    max_rows: Annotated[int, Query(ge=1, le=100000)] = 20000,
    min_training_samples: Annotated[int, Query(ge=5)] = 20,
    test_ratio: Annotated[float, Query(gt=0.0, lt=0.9)] = 0.2,
    n_estimators: Annotated[int, Query(ge=10, le=500)] = 100,
    session: Session = Depends(get_session),
) -> ChartResponse[dict[str, Any]]:
    start_dt, end_dt = filters.to_datetime_bounds()
    polygon_wkt = filters.polygon_wkt
    repo = HotspotRepository(session)
    stmt_kwargs: dict[str, Any] = {}
    if filters.country is not None:
        stmt_kwargs["country"] = filters.country
    if polygon_wkt is not None:
        stmt_kwargs["polygon_wkt"] = polygon_wkt

    rows_iter = repo.iter_hotspots_filtered(
        start_date=start_dt,
        end_date=end_dt,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        max_rows=max_rows,
        **stmt_kwargs,
    )

    prepared = HotspotProcessor().prepare(rows_iter)
    if prepared.is_empty:
        raise HTTPException(
            status_code=422, detail="No hay hotspots válidos en el rango indicado."
        )

    clusterer = FireClusterer(
        eps_km=eps_km,
        min_samples=min_samples,
        time_window_hours=time_window_hours,
        max_time_window_hours=max_time_window_hours,
    )
    clustering = clusterer.fit_predict(prepared)
    trajectories = FireMovementAnalyzer(interval_hours=interval_hours).analyze_all(
        prepared, clustering.labels
    )

    all_steps = [step for steps in trajectories.values() for step in steps]
    if len(all_steps) < 2:
        raise HTTPException(
            status_code=422,
            detail="Trayectorias insuficientes para análisis meteorológico y predicción.",
        )

    min_dt = min(s.timestamp for s in all_steps)
    max_dt = max(s.timestamp for s in all_steps)
    mean_lat = sum(s.centroid_lat for s in all_steps) / len(all_steps)
    mean_lon = sum(s.centroid_lon for s in all_steps) / len(all_steps)

    weather_client = WeatherDataClient()
    try:
        daily_records = await weather_client.fetch_daily_records(
            RequestWeather(
                latitude=mean_lat, longitude=mean_lon, start=min_dt, end=max_dt
            )
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
        n_estimators=n_estimators,
        min_training_samples=min_training_samples,
    )
    try:
        metrics = predictor.train_and_evaluate(dataset, test_ratio=test_ratio)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    last_features = dataset.X[-1]
    prediction = predictor.predict(last_features)

    return build_chart_response(
        "models.predict",
        {
            "metrics": asdict(metrics),
            "latest_prediction": asdict(prediction),
        },
        filters,
        extra_filters={
            "eps_km": eps_km,
            "min_samples": min_samples,
            "interval_hours": interval_hours,
            "n_estimators": n_estimators,
            "test_ratio": test_ratio,
        },
    )
