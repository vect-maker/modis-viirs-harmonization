from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

try:
    from .ClusterStatus import ClusterStatus
except ImportError:
    from model.ClusterStatus import ClusterStatus

if TYPE_CHECKING:
    from model.ClusterHotspot import ClusterHotspots
    from model.EnvironmentalRecord import EnvironmentalRecord
    from model.FireClusterForecast import FireClusterForecast


class FireCluster(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    hotspots: list["ClusterHotspots"] = Relationship(back_populates="cluster")

    polygon: float = Field(nullable=False)
    status: ClusterStatus = Field(default=ClusterStatus.ACTIVO, nullable=False)
    datetimeStart: datetime | None = Field(default=None, nullable=True)
    datetimeEnd: datetime | None = Field(default=None, nullable=True)
    maxFrp: float | None = Field(default=None, nullable=True)

    environmentalRecords: list["EnvironmentalRecord"] = Relationship(
        back_populates="fireCluster",
        sa_relationship_kwargs={"foreign_keys": "[EnvironmentalRecord.fireClusterId]"},
    )

    forecasts: list["FireClusterForecast"] = Relationship(
        back_populates="fireCluster",
        sa_relationship_kwargs={
            "foreign_keys": "[FireClusterForecast.fireClusterId]"
        },
    )

    dirExpansion: float | None = Field(default=None, nullable=True)
    veloExpansion: float | None = Field(default=None, nullable=True)

    area_km2: float = Field(default=0.0, nullable=False)
    centroid_lat: float | None = Field(default=None, nullable=True)
    centroid_lon: float | None = Field(default=None, nullable=True)
    hotspot_count: int = Field(default=0, nullable=False)
    modis_count: int = Field(default=0, nullable=False)
    viirs_count: int = Field(default=0, nullable=False)
    total_frp: float | None = Field(default=None, nullable=True)
    harmonized_weight: float | None = Field(default=None, nullable=True)
