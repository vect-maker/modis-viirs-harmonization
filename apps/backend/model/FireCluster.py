from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from model.ClusterStatus import ClusterStatus

if TYPE_CHECKING:
    from model.ClusterHotspot import ClusterHotspots
    from model.EnvironmentalRecord import EnvironmentalRecord


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
        sa_relationship_kwargs={
            "foreign_keys": "[EnvironmentalRecord.fireClusterId]"
        },
    )

    dirExpansion: float | None = Field(default=None, nullable=True)
    veloExpansion: float | None = Field(default=None, nullable=True)