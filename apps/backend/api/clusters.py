import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, col, func, select

from database.session import get_session
from model import ClusterHotspots, FireCluster, Hotspots
from model.ClusterStatus import ClusterStatus
from repositories.pagination import paginate_statement
from schemas.pagination import PaginatedResponse, PaginationDep

router = APIRouter(prefix="/clusters", tags=["Clusters"])


class ClusterGeoJsonQuery(BaseModel):
    bbox: list[float] | None = None
    aoi: dict[str, Any] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: ClusterStatus | None = None
    min_hotspots: int = 1
    limit: int = 500


def _parse_bbox(bbox_str: str | None) -> tuple[float, float, float, float] | None:
    if not bbox_str:
        return None
    parts = [p.strip() for p in bbox_str.split(",")]
    if len(parts) != 4:
        raise HTTPException(
            status_code=422,
            detail="bbox must have 4 comma-separated floats: min_lon,min_lat,max_lon,max_lat",
        )
    try:
        min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid numeric values in bbox") from exc
    return min_lon, min_lat, max_lon, max_lat


def _query_clusters_geojson(
    session: Session,
    bbox: tuple[float, float, float, float] | None,
    aoi: dict[str, Any] | None,
    start_date: datetime | None,
    end_date: datetime | None,
    status: ClusterStatus | None,
    min_hotspots: int,
    limit: int,
) -> dict[str, Any]:
    dialect = session.get_bind().dialect.name
    safe_limit = max(1, min(limit, 2000))

    if dialect == "postgresql":
        where_clauses = ["hotspot_count >= :min_hotspots"]
        params: dict[str, Any] = {
            "min_hotspots": min_hotspots,
            "limit": safe_limit,
        }

        if status is not None:
            where_clauses.append("status = :status")
            params["status"] = status.value

        if start_date is not None:
            where_clauses.append('COALESCE("datetimeEnd", "datetimeStart") >= :start_date')
            params["start_date"] = start_date

        if end_date is not None:
            where_clauses.append('"datetimeStart" <= :end_date')
            params["end_date"] = end_date

        if bbox is not None:
            min_lon, min_lat, max_lon, max_lat = bbox
            where_clauses.append(
                "geom IS NOT NULL AND ST_Intersects(geom, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"
            )
            params.update(
                min_lon=min_lon,
                min_lat=min_lat,
                max_lon=max_lon,
                max_lat=max_lat,
            )

        if aoi is not None:
            where_clauses.append(
                "geom IS NOT NULL AND ST_Intersects(geom, ST_SetSRID(ST_GeomFromGeoJSON(:aoi_json), 4326))"
            )
            params["aoi_json"] = json.dumps(aoi)

        where_sql = " AND ".join(where_clauses)
        sql = text(
            f"""
            SELECT
                id,
                status::text AS status,
                "datetimeStart" AS datetime_start,
                "datetimeEnd" AS datetime_end,
                ROUND((EXTRACT(EPOCH FROM ("datetimeEnd" - "datetimeStart")) / 3600.0)::numeric, 2)::double precision AS duration_h,
                "maxFrp" AS max_frp,
                total_frp,
                harmonized_weight,
                area_km2,
                centroid_lat,
                centroid_lon,
                hotspot_count,
                modis_count,
                viirs_count,
                ST_AsGeoJSON(geom) AS geom_json,
                ST_AsGeoJSON(centroid) AS centroid_json
            FROM firecluster
            WHERE {where_sql}
            ORDER BY COALESCE("datetimeEnd", "datetimeStart") DESC NULLS LAST, id DESC
            LIMIT :limit
            """
        )

        rows = session.execute(sql, params).mappings().all()
        features = []
        for row in rows:
            geometry = (
                json.loads(row["geom_json"])
                if row["geom_json"]
                else (json.loads(row["centroid_json"]) if row["centroid_json"] else None)
            )
            if geometry is None:
                continue
            features.append(
                {
                    "type": "Feature",
                    "id": row["id"],
                    "geometry": geometry,
                    "properties": {
                        "id": row["id"],
                        "status": row["status"],
                        "datetime_start": row["datetime_start"].isoformat() if row["datetime_start"] else None,
                        "datetime_end": row["datetime_end"].isoformat() if row["datetime_end"] else None,
                        "duration_h": row["duration_h"] or 0.0,
                        "max_frp": row["max_frp"],
                        "total_frp": row["total_frp"],
                        "harmonized_weight": row["harmonized_weight"],
                        "area_km2": row["area_km2"],
                        "centroid_lat": row["centroid_lat"],
                        "centroid_lon": row["centroid_lon"],
                        "hotspot_count": row["hotspot_count"],
                        "modis_count": row["modis_count"],
                        "viirs_count": row["viirs_count"],
                    },
                }
            )
        return {"type": "FeatureCollection", "features": features}

    # SQLite / non-PostGIS fallback for unit tests
    stmt = select(FireCluster).where(col(FireCluster.hotspot_count) >= min_hotspots)
    if status is not None:
        stmt = stmt.where(FireCluster.status == status)
    if start_date is not None:
        stmt = stmt.where(
            func.coalesce(col(FireCluster.datetimeEnd), col(FireCluster.datetimeStart)) >= start_date
        )
    if end_date is not None:
        stmt = stmt.where(col(FireCluster.datetimeStart) <= end_date)
    if bbox is not None:
        min_lon, min_lat, max_lon, max_lat = bbox
        stmt = stmt.where(
            col(FireCluster.centroid_lon) >= min_lon,
            col(FireCluster.centroid_lon) <= max_lon,
            col(FireCluster.centroid_lat) >= min_lat,
            col(FireCluster.centroid_lat) <= max_lat,
        )

    stmt = stmt.order_by(col(FireCluster.id).desc()).limit(safe_limit)
    clusters = session.exec(stmt).all()
    features = []
    for c in clusters:
        if c.centroid_lon is None or c.centroid_lat is None:
            continue
        duration_h = 0.0
        if c.datetimeStart and c.datetimeEnd:
            duration_h = round((c.datetimeEnd - c.datetimeStart).total_seconds() / 3600.0, 2)
        features.append(
            {
                "type": "Feature",
                "id": c.id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [c.centroid_lon, c.centroid_lat],
                },
                "properties": {
                    "id": c.id,
                    "status": c.status.value,
                    "datetime_start": c.datetimeStart.isoformat() if c.datetimeStart else None,
                    "datetime_end": c.datetimeEnd.isoformat() if c.datetimeEnd else None,
                    "duration_h": duration_h,
                    "max_frp": c.maxFrp,
                    "total_frp": c.total_frp,
                    "harmonized_weight": c.harmonized_weight,
                    "area_km2": c.area_km2,
                    "centroid_lat": c.centroid_lat,
                    "centroid_lon": c.centroid_lon,
                    "hotspot_count": c.hotspot_count,
                    "modis_count": c.modis_count,
                    "viirs_count": c.viirs_count,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/geojson", summary="Fire Events como GeoJSON")
async def get_clusters_geojson(
    bbox: str | None = Query(default=None, description="min_lon,min_lat,max_lon,max_lat"),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    status: ClusterStatus | None = Query(default=None),
    min_hotspots: int = Query(default=1, ge=0),
    limit: int = Query(default=500, ge=1, le=2000),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Retorna los Fire Events agrupados como GeoJSON FeatureCollection filtrable por bbox y fechas."""
    parsed_bbox = _parse_bbox(bbox)
    return _query_clusters_geojson(
        session=session,
        bbox=parsed_bbox,
        aoi=None,
        start_date=start_date,
        end_date=end_date,
        status=status,
        min_hotspots=min_hotspots,
        limit=limit,
    )


@router.post("/geojson", summary="Consultar Fire Events por AOI GeoJSON")
async def query_clusters_geojson(
    payload: ClusterGeoJsonQuery = Body(...),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Consulta Fire Events interceptando un polígono GeoJSON (AOI) o bbox y rango de fechas."""
    parsed_bbox: tuple[float, float, float, float] | None = None
    if payload.bbox is not None:
        if len(payload.bbox) != 4:
            raise HTTPException(status_code=422, detail="bbox must contain 4 numbers")
        parsed_bbox = (
            float(payload.bbox[0]),
            float(payload.bbox[1]),
            float(payload.bbox[2]),
            float(payload.bbox[3]),
        )
    return _query_clusters_geojson(
        session=session,
        bbox=parsed_bbox,
        aoi=payload.aoi,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        min_hotspots=payload.min_hotspots,
        limit=payload.limit,
    )


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

    base_stmt = (
        select(Hotspots)
        .join(ClusterHotspots, col(ClusterHotspots.hotspotsId) == col(Hotspots.id))
        .where(ClusterHotspots.clusterId == cluster_id)
    )
    total = session.exec(select(func.count()).select_from(base_stmt.subquery())).one()
    hotspot_stmt = (
        base_stmt.order_by(col(Hotspots.acq_datetime), col(Hotspots.id))
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    hotspots = session.exec(hotspot_stmt).all()

    return {
        "data": {
            "cluster": cluster,
            "hotspots": hotspots,
        },
        "total": total,
        "limit": pagination.limit,
        "offset": pagination.offset,
    }
